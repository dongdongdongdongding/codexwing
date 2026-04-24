import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta

# Load env variables
load_dotenv()
load_dotenv(".env.local")

class DBManager:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY")
        self.client: Client = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                print("✅ Connected to Supabase")
            except Exception as e:
                print(f"❌ Supabase Connection Failed: {e}")
        self._table_columns_cache = {}

    def _get_table_columns(self, table_name):
        if table_name in self._table_columns_cache:
            return self._table_columns_cache[table_name]
        if not self.client:
            self._table_columns_cache[table_name] = set()
            return set()
        try:
            response = self.client.table(table_name).select("*").limit(1).execute()
            rows = response.data or []
            cols = set(rows[0].keys()) if rows else set()
            self._table_columns_cache[table_name] = cols
            return cols
        except Exception:
            self._table_columns_cache[table_name] = set()
            return set()

    def _filter_payload_to_existing_columns(self, table_name, payload):
        if not isinstance(payload, dict):
            return {}
        known = self._get_table_columns(table_name)
        if not known:
            return payload
        return {k: v for k, v in payload.items() if k in known}

    def _classify_decision_bucket(self, decision):
        value = str(decision or "").strip().upper()
        if value == "EXCEPTION_LEADER":
            return "exception_leader"
        if value in {"WATCHLIST_ONLY", "FALLBACK_WATCHLIST", "WATCHLIST", "OBSERVE"}:
            return "watchlist"
        if value in {"PRIORITY_WATCHLIST"}:
            return "picked"
        return "ignored"

    def _archive_market_type(self, market_value, ticker):
        market = str(market_value or "").upper()
        if market in {"KOSPI", "KOSDAQ", "KR"}:
            return "KR"
        if market == "AMEX":
            return "AMEX"
        if market in {"NASDAQ", "NYSE", "US"}:
            return "US"
        t = str(ticker or "").upper()
        if t.endswith(".KS") or t.endswith(".KQ"):
            return "KR"
        return "US"

    def _resolve_submarket(self, market_value, market_type, ticker):
        raw = str(market_value or "").upper()
        if raw in {"KOSPI", "KOSDAQ"}:
            return raw
        mt = str(market_type or "").upper()
        t = str(ticker or "").upper()
        if mt in {"KR", "KOSPI", "KOSDAQ"} or t.endswith(".KS") or t.endswith(".KQ"):
            if t.endswith(".KS"):
                return "KOSPI"
            if t.endswith(".KQ"):
                return "KOSDAQ"
        return None

    def _to_int_or_none(self, value):
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except Exception:
            return None

    def _to_float_or_none(self, value):
        try:
            if value is None or value == "":
                return None
            result = float(value)
            if result != result:
                return None
            return result
        except Exception:
            return None

    def _feature_quality_payload(self, data, origin="scanner_full"):
        required = {
            "alpha_score": data.get("alpha_score"),
            "tech_score": data.get("tech_score"),
            "ml_prob": data.get("ml_prob"),
            "whale_score": data.get("whale_score"),
            "trend": data.get("initial_trend") or data.get("trend") or data.get("real_trend"),
            "volume_ratio": data.get("volume_ratio"),
            "position": data.get("position"),
            "tier": data.get("tier"),
            "decision_score": data.get("decision_score"),
            "entry_reference_price": data.get("entry_reference_price"),
        }
        missing = []
        for key, value in required.items():
            if isinstance(value, bool):
                continue
            if value is None:
                missing.append(key)
                continue
            if isinstance(value, str) and value.strip().lower() in {"", "?", "nan", "none", "null", "unknown", "na", "n/a"}:
                missing.append(key)
        completeness = 1.0 if not required else (len(required) - len(missing)) / len(required)
        reason = data.get("validation_excluded_reason")
        if not reason and missing:
            reason = "FEATURE_MISSING:" + ",".join(missing)
        validation_excluded = data.get("validation_excluded")
        if validation_excluded is None:
            validation_excluded = bool(missing)
        return {
            "feature_origin": data.get("feature_origin") or origin,
            "feature_quality": data.get("feature_quality") or ("complete" if not missing else "incomplete"),
            "feature_completeness": data.get("feature_completeness") if data.get("feature_completeness") is not None else round(float(completeness), 4),
            "feature_missing_fields": data.get("feature_missing_fields") if data.get("feature_missing_fields") is not None else missing,
            "validation_excluded": bool(validation_excluded),
            "validation_excluded_reason": reason,
            "is_dummy_data": bool(data.get("is_dummy_data", False)),
        }
    
    def save_signal(self, ticker, price, alpha_score, ai_prediction, signal_type="BUY", stock_name=None, 
                   entry_price=None, target_price=None, stop_loss=None):
        """
        Save a trading signal to 'signals' table.
        Table Schema: id, created_at, ticker, stock_name, price, alpha_score, ai_prediction, signal_type, result_3d,
                     entry_price, target_price, stop_loss
        """
        if not self.client: return
        
        data = {
            "ticker": ticker,
            "stock_name": stock_name if stock_name else ticker,
            "price": float(price),
            "alpha_score": int(alpha_score),
            "ai_prediction": float(ai_prediction),
            "signal_type": signal_type,
            "entry_price": float(entry_price) if entry_price else None,
            "target_price": float(target_price) if target_price else None,
            "stop_loss": float(stop_loss) if stop_loss else None,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            self.client.table("signals").insert(data).execute()
            print(f"💾 Signal Saved: {ticker} ({stock_name})")
        except Exception as e:
            print(f"Error saving signal: {e}")

    def save_market_features(self, data_dict):
        """
        Save comprehensive market features to 'market_features' table.
        Used for building ML training dataset.
        """
        if not self.client: return
        
        # Handle NaN/Infinite values for JSON safety
        import math
        clean_data = {}
        for k, v in data_dict.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean_data[k] = None
            else:
                clean_data[k] = v
                
        clean_data["created_at"] = datetime.now().isoformat()
        
        try:
            self.client.table("market_features").insert(clean_data).execute()
            # print(f"💾 Features Logged: {clean_data.get('ticker')}")
        except Exception as e:
            print(f"Error saving market features: {e}")

    def update_performance(self):
        """
        Check past signals (older than 3 days) and update 'result_3d'.
        This simulates 'Paper Trading' results.
        """
        if not self.client: return
        
        # 1. Fetch pending signals (older than 3 days, result is null)
        try:
            # Supabase query: result_3d is null
            response = self.client.table("signals").select("*").is_("result_3d", "null").execute()
            signals = response.data
            
            if not signals: return
            
            import yfinance as yf
            
            for sig in signals:
                ticker = sig['ticker']
                entry_date = pd.to_datetime(sig['created_at']).tz_localize(None)
                entry_price = sig['price']
                
                # Check if 3 days have passed
                if (datetime.now() - entry_date).days >= 3:
                    # Get current price
                    # Optimization: Could fetch batch, but simple loop for now
                    df = yf.download(ticker, period="5d", progress=False)
                    if df.empty: continue
                    
                    curr_price = df['Close'].iloc[-1]
                    ret = ((curr_price - entry_price) / entry_price) * 100
                    
                    # Update DB
                    self.client.table("signals").update({"result_3d": ret}).eq("id", sig['id']).execute()
                    print(f"📝 Updated Result for {ticker}: {ret:.2f}%")
                    
        except Exception as e:
            print(f"Error updating performance: {e}")

    def fetch_dashboard_data(self):
        """
        Fetch data for Streamlit Dashboard.
        Returns: 
           - recent_signals (DataFrame)
           - win_rate (float)
           - total_profit (float)
        """
        if not self.client: return pd.DataFrame(), 0, 0
        
        try:
            # Fetch all signals
            response = self.client.table("signals").select("*").order("created_at", desc=True).limit(100).execute()
            df = pd.DataFrame(response.data)
            
            if df.empty: return df, 0, 0
            
            # Calculate Win Rate (result_3d > 0)
            completed = df[df['result_3d'].notnull()]
            if completed.empty:
                win_rate = 0
                avg_profit = 0
            else:
                wins = len(completed[completed['result_3d'] > 0])
                win_rate = (wins / len(completed)) * 100
                avg_profit = completed['result_3d'].mean()
            
            return df, win_rate, avg_profit
            
        except Exception as e:
            print(f"Dashboard Fetch Error: {e}")
            return pd.DataFrame(), 0, 0
            
    def upsert_scan_result(self, data):
        """
        Upsert scan result — prevents duplicate rows for same ticker within same session.
        Uses on_conflict='ticker' so repeated scans update the existing row instead of inserting.
        NOTE: Supabase requires a UNIQUE constraint on 'ticker' col, OR we manually delete+insert.
        We use a delete-then-insert strategy keyed on ticker to ensure clean dedup.
        """
        if not self.client: return

        try:
            from modules.db_schema import build_scan_result_payload, DEFAULT_FALLBACK_KEYS

            ticker = data.get('ticker')
            feature_quality = self._feature_quality_payload(data, origin=data.get("feature_origin") or "scanner_full")
            submarket = self._resolve_submarket(data.get('market'), data.get('market_type'), ticker)
            overrides = {
                "market": submarket,
                "created_at": datetime.now().isoformat(),
                **feature_quality,
            }
            payload = build_scan_result_payload(data, overrides=overrides, fallback_keys=DEFAULT_FALLBACK_KEYS)
            payload = self._filter_payload_to_existing_columns("market_scan_results", payload)

            # Delete the current run's row when run_id exists; otherwise fall back to same-day ticker dedupe.
            from datetime import datetime as dt
            run_id = str(data.get("run_id") or "").strip()
            delete_query = self.client.table("market_scan_results").delete().eq("ticker", ticker)
            if run_id:
                delete_query = delete_query.eq("run_id", run_id)
            else:
                today_start = dt.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
                delete_query = delete_query.gte("created_at", today_start)
            delete_query.execute()

            # Now insert fresh
            self.client.table("market_scan_results").insert(payload).execute()
            print(f"☁️ DB Upserted: {data.get('name', ticker)} [{data.get('market_type')}]")

        except Exception as e:
            print(f"⚠️ DB Upsert Error: {e}")



    def get_ticker_history(self, ticker):
        """Phase 13: Fetch historical scan results for a ticker"""
        if not self.client: return []
        try:
            # Fetch last 30 records
            res = self.client.table("market_scan_results")\
                .select("alpha_score, ml_prob, whale_score, created_at, trend")\
                .eq("ticker", ticker)\
                .order("created_at", desc=True)\
                .limit(30)\
                .execute()
            return res.data[::-1] # Return reversed (Chronological)
        except Exception as e:
            print(f"History Fetch Error: {e}")
            return []

    def get_market_stats(self, market_type="KR"):
        """Phase 13: Get today's market average stats"""
        if not self.client: return {}
        try:
            # Fetch recent 200 records for the market to estimate avg
            # Ideal: Server-side aggregation, but client-side is easier for now
            res = self.client.table("market_scan_results")\
                .select("alpha_score, ml_prob, whale_score")\
                .eq("market_type", market_type)\
                .order("created_at", desc=True)\
                .limit(200)\
                .execute()
            
            data = res.data
            if not data: return {}
            
            df = pd.DataFrame(data)
            return {
                "avg_alpha": df['alpha_score'].mean(),
                "avg_whale": df['whale_score'].mean(),
                "avg_ml": df['ml_prob'].mean()
            }
        except Exception as e:
            print(f"Market Stats Error: {e}")
            return {}

    def _json_safe(self, value):
        """Convert values to JSON-safe payloads for Supabase inserts."""
        import math

        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._json_safe(v) for v in value]
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return float(value)
        if isinstance(value, (int, str, bool)) or value is None:
            return value
        return str(value)

    def save_agent_run_summary(self, row):
        """
        Save multi-agent run summary row.
        Target table: agent_run_summaries (run_id unique)
        """
        if not self.client:
            return False

        payload = {
            "run_id": row.get("run_id"),
            "market": row.get("market"),
            "strategy_version": row.get("strategy_version"),
            "model_version": row.get("model_version"),
            "code_version": row.get("code_version"),
            "artifact_refs": self._json_safe(row.get("artifact_refs", {})),
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.client.table("agent_run_summaries").upsert(payload, on_conflict="run_id").execute()
            return True
        except Exception as e:
            print(f"Agent Run Summary Save Error: {e}")
            return False

    def save_agent_postmortem(self, row):
        """
        Save multi-agent postmortem row.
        Target table: agent_postmortems (run_id unique)
        """
        if not self.client:
            return False

        payload = {
            "run_id": row.get("run_id"),
            "market": row.get("market"),
            "scope": row.get("scope"),
            "failure_summary": row.get("failure_summary"),
            "likely_causes": self._json_safe(row.get("likely_causes", [])),
            "evidence_refs": self._json_safe(row.get("evidence_refs", [])),
            "produced_at": row.get("produced_at"),
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.client.table("agent_postmortems").upsert(payload, on_conflict="run_id").execute()
            return True
        except Exception as e:
            print(f"Agent Postmortem Save Error: {e}")
            return False

    def save_agent_improvement_tickets(self, tickets):
        """
        Save multi-agent improvement tickets.
        Target table: agent_improvement_tickets (ticket_id unique)
        """
        if not self.client:
            return 0
        if not tickets:
            return 0

        rows = []
        for ticket in tickets:
            rows.append(
                {
                    "ticket_id": ticket.get("ticket_id"),
                    "run_id": ticket.get("run_id"),
                    "owner_agent": ticket.get("owner_agent"),
                    "owner_module": ticket.get("owner_module"),
                    "title": ticket.get("title"),
                    "hypothesis": ticket.get("hypothesis"),
                    "requested_change": ticket.get("requested_change"),
                    "priority": ticket.get("priority"),
                    "status": ticket.get("status"),
                    "created_at": ticket.get("created_at") or datetime.now().isoformat(),
                }
            )

        try:
            self.client.table("agent_improvement_tickets").upsert(rows, on_conflict="ticket_id").execute()
            return len(rows)
        except Exception as e:
            print(f"Agent Ticket Save Error: {e}")
            return 0

    def get_latest_resolved_signal_outcome(self, ticker, since_iso=None, limit=50):
        """
        Fetch latest resolved signal outcome for a ticker from 'signals' table.
        Returns a dict with result_3d when available, else None.
        """
        if not self.client:
            return None

        try:
            query = self.client.table("signals")\
                .select("id, ticker, stock_name, created_at, result_3d, signal_type")\
                .eq("ticker", ticker)
            if since_iso:
                query = query.gte("created_at", since_iso)
            query = query.order("created_at", desc=True).limit(int(limit))
            res = query.execute()
            rows = res.data if res and hasattr(res, "data") and res.data else []
            if not rows:
                return None

            for row in rows:
                if row.get("result_3d") is None:
                    continue
                try:
                    ret = float(row.get("result_3d"))
                except Exception:
                    continue
                return {
                    "signal_id": row.get("id"),
                    "ticker": row.get("ticker"),
                    "stock_name": row.get("stock_name"),
                    "created_at": row.get("created_at"),
                    "result_3d": ret,
                    "signal_type": row.get("signal_type"),
                }
            return None
        except Exception as e:
            print(f"Resolved Signal Fetch Error ({ticker}): {e}")
            return None

    def save_agent_realized_outcomes(self, run_id, outcomes):
        """
        Upsert realized outcomes for a run.
        Target table: agent_realized_outcomes (outcome_key unique)
        """
        if not self.client:
            return 0
        if not outcomes:
            return 0

        rows = []
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            priority_rank = int(row.get("priority_rank", 0) or 0)
            outcome_key = f"{run_id}:{ticker}:{priority_rank}"
            rows.append(
                self._filter_payload_to_existing_columns("agent_realized_outcomes", {
                    "outcome_key": outcome_key,
                    "run_id": run_id,
                    "ticker": ticker,
                    "market": row.get("market"),
                    "stock_name": row.get("stock_name"),
                    "scan_mode": row.get("scan_mode"),
                    "strategy_family": row.get("strategy_family"),
                    "priority_rank": priority_rank,
                    "decision": row.get("decision"),
                    "decision_bucket": row.get("decision_bucket") or self._classify_decision_bucket(row.get("decision")),
                    "status": row.get("status"),
                    "horizon": row.get("horizon"),
                    "recommended_at": row.get("recommended_at"),
                    "realized_return_pct": row.get("realized_return_pct"),
                    "base_trade_date": row.get("base_trade_date"),
                    "entry_reference_price": row.get("entry_reference_price"),
                    "latest_return_pct": row.get("latest_return_pct"),
                    "return_30m_pct": row.get("return_30m_pct"),
                    "return_1h_pct": row.get("return_1h_pct"),
                    "return_close_pct": row.get("return_close_pct"),
                    "return_1d_pct": row.get("return_1d_pct"),
                    "return_2d_pct": row.get("return_2d_pct"),
                    "return_3d_pct": row.get("return_3d_pct"),
                    "return_5d_pct": row.get("return_5d_pct"),
                    "return_7d_pct": row.get("return_7d_pct"),
                    "quant_priority_score": row.get("quant_priority_score"),
                    "quant_score_1d": row.get("quant_score_1d"),
                    "quant_score_3d": row.get("quant_score_3d"),
                    "selection_lane": row.get("selection_lane"),
                    "target_horizon_days": row.get("target_horizon_days"),
                    "scanner_timeframe_profile": row.get("scanner_timeframe_profile"),
                    "kr_universe_role": row.get("kr_universe_role"),
                    "explosive_eligible": row.get("explosive_eligible"),
                    "explosive_gate_reasons": row.get("explosive_gate_reasons"),
                    "continuation_eligible": row.get("continuation_eligible"),
                    "continuation_enabled": row.get("continuation_enabled"),
                    "continuation_prob_3d": row.get("continuation_prob_3d"),
                    "continuation_evidence": row.get("continuation_evidence"),
                    "continuation_gate_reasons": row.get("continuation_gate_reasons"),
                    "outcome_label": row.get("outcome_label"),
                    "outcome_recorded_at": row.get("outcome_recorded_at"),
                    "source_ref": row.get("source_ref"),
                    "quality_flags": row.get("quality_flags"),
                    "validation_excluded": row.get("validation_excluded"),
                    "resolved_signal_created_at": row.get("resolved_signal_created_at"),
                    "resolved_signal_type": row.get("resolved_signal_type"),
                    "resolved_stock_name": row.get("resolved_stock_name"),
                    "updated_at": datetime.now().isoformat(),
                })
            )

        if not rows:
            return 0

        try:
            self.client.table("agent_realized_outcomes").upsert(rows, on_conflict="outcome_key").execute()
            return len(rows)
        except Exception as e:
            print(f"Agent Realized Outcomes Save Error: {e}")
            return 0

    def upsert_scan_archive_outcomes(self, run_id, market, outcomes):
        """
        Sync run outcomes into market_scan_results so Scan Archive can show
        picked/watchlist/exception-leader classification and realized returns.
        """
        if not self.client:
            return 0
        if not outcomes:
            return 0

        updated = 0
        for row in outcomes:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip()
            if not ticker:
                continue
            recommended_at = row.get("recommended_at")
            rec_dt = None
            try:
                rec_dt = pd.to_datetime(recommended_at)
            except Exception:
                rec_dt = None
            if rec_dt is None or pd.isna(rec_dt):
                rec_dt = pd.Timestamp.utcnow()
            if getattr(rec_dt, "tzinfo", None) is None:
                rec_dt = rec_dt.tz_localize("UTC")
            from modules.db_schema import build_scan_result_payload, DEFAULT_FALLBACK_KEYS
            # Translate outcome-row keys → SCAN_RESULT_COLUMNS source-key conventions.
            # Keep `row` intact; build a thin adapter dict.
            schema_data = {
                **row,
                "name": row.get("stock_name") or row.get("resolved_stock_name") or ticker,
                "note": row.get("source_ref"),                # strategy ← source_ref
                "initial_trend": row.get("real_trend"),       # trend ← real_trend
                "ml_prob": row.get("prob_5"),                 # ml_prob ← prob_5
                "outcome_status": row.get("status"),          # outcome_status ← status
                "volume": row.get("volume") if row.get("volume") is not None else row.get("volume_ratio"),
            }
            overrides = {
                "run_id": run_id,
                "market": row.get("market"),
                "market_type": self._archive_market_type(market, ticker),
                "created_at": recommended_at or rec_dt.isoformat(),
                "recommended_at": recommended_at,
                "priority_rank": int(row.get("priority_rank", 0) or 0),
                "decision_bucket": row.get("decision_bucket") or self._classify_decision_bucket(row.get("decision")),
                "is_dummy_data": bool(row.get("is_dummy_data", False)),
            }
            payload = build_scan_result_payload(schema_data, overrides=overrides, fallback_keys=DEFAULT_FALLBACK_KEYS)
            origin = "scanner_archive_outcome" if payload.get("alpha_score") is not None else "outcome_sync_partial"
            payload.update(self._feature_quality_payload(payload, origin=origin))
            payload = self._filter_payload_to_existing_columns("market_scan_results", payload)
            if not payload:
                continue
            try:
                existing = (
                    self.client.table("market_scan_results")
                    .select("id")
                    .eq("run_id", run_id)
                    .eq("ticker", ticker)
                    .eq("scan_mode", row.get("scan_mode"))
                    .eq("strategy_family", row.get("strategy_family"))
                    .eq("priority_rank", int(row.get("priority_rank", 0) or 0))
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                rows = existing.data or []
                # Fallback: scanner_full row from the same scan session has run_id=NULL
                # (worker writes before orchestrator generates run_id). Match by
                # ticker+scan_mode+date so we can UPDATE that row instead of inserting a
                # duplicate scanner_archive_outcome stub. Restrict to NULL-run scanner rows
                # so we never re-merge into an already-bound row from a different session.
                if not rows:
                    scan_mode_val = row.get("scan_mode")
                    rec_date = (recommended_at or rec_dt.isoformat())[:10]
                    fallback_q = (
                        self.client.table("market_scan_results")
                        .select("id")
                        .eq("ticker", ticker)
                        .is_("run_id", "null")
                        .gte("created_at", f"{rec_date}T00:00:00")
                        .lte("created_at", f"{rec_date}T23:59:59.999999")
                    )
                    if scan_mode_val:
                        fallback_q = fallback_q.eq("scan_mode", scan_mode_val)
                    fallback_q = fallback_q.in_("feature_origin", ["scanner_full", "scanner_partial_legacy"])
                    fallback = fallback_q.order("created_at", desc=True).limit(1).execute()
                    rows = fallback.data or []
                if rows:
                    row_id = rows[0].get("id")
                    existing_row = (
                        self.client.table("market_scan_results")
                        .select("*")
                        .eq("id", row_id)
                        .limit(1)
                        .execute()
                    )
                    existing_payload = {}
                    if existing_row and getattr(existing_row, "data", None):
                        existing_payload = dict(existing_row.data[0] or {})
                    merged_payload = dict(existing_payload)
                    for key, value in payload.items():
                        if value is None:
                            continue
                        if isinstance(value, str) and not value.strip():
                            continue
                        merged_payload[key] = value
                    merged_payload = self._filter_payload_to_existing_columns("market_scan_results", merged_payload)
                    self.client.table("market_scan_results").update(merged_payload).eq("id", row_id).execute()
                else:
                    self.client.table("market_scan_results").insert(payload).execute()
                updated += 1
            except Exception as e:
                print(f"Scan Archive Outcome Sync Error ({ticker}): {e}")
        return updated

    def update_run_quality_flags(self, run_id, market, quality_flags=None, validation_excluded=False):
        if not self.client or not run_id:
            return False
        flags = quality_flags if isinstance(quality_flags, list) else []
        payload_archive = self._filter_payload_to_existing_columns(
            "market_scan_results",
            {
                "market": market,
                "quality_flags": flags,
                "validation_excluded": bool(validation_excluded),
            },
        )
        payload_outcomes = self._filter_payload_to_existing_columns(
            "agent_realized_outcomes",
            {
                "market": market,
                "quality_flags": flags,
                "validation_excluded": bool(validation_excluded),
            },
        )
        try:
            if payload_archive:
                self.client.table("market_scan_results").update(payload_archive).eq("run_id", run_id).execute()
            if payload_outcomes:
                self.client.table("agent_realized_outcomes").update(payload_outcomes).eq("run_id", run_id).execute()
            return True
        except Exception as e:
            print(f"Run Quality Flag Update Error ({run_id}): {e}")
            return False

    def save_agent_profile_diagnostics(self, row):
        """
        Upsert profile diagnostics for a run.
        Target table: agent_profile_diagnostics (run_id unique)
        """
        if not self.client:
            return False
        if not isinstance(row, dict):
            return False

        payload = {
            "run_id": row.get("run_id"),
            "market": row.get("market"),
            "current_profile": row.get("current_profile"),
            "current_total_scans": row.get("current_total_scans"),
            "current_result_count": row.get("current_result_count"),
            "current_top_reject_reason": self._json_safe(row.get("current_top_reject_reason", {})),
            "profile_summary": self._json_safe(row.get("profile_summary", {})),
            "flags": self._json_safe(row.get("flags", {})),
            "fallback_watchlist": self._json_safe(row.get("fallback_watchlist", {})),
            "generated_at": row.get("generated_at"),
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.client.table("agent_profile_diagnostics").upsert(payload, on_conflict="run_id").execute()
            return True
        except Exception as e:
            print(f"Agent Profile Diagnostics Save Error: {e}")
            return False

    def save_agent_outcome_health(self, row):
        """
        Upsert outcome health diagnostics for a run.
        Target table: agent_outcome_health (run_id unique)
        """
        if not self.client:
            return False
        if not isinstance(row, dict):
            return False

        payload = {
            "run_id": row.get("run_id"),
            "market": row.get("market"),
            "window_runs": row.get("window_runs"),
            "runs_with_outcomes": row.get("runs_with_outcomes"),
            "outcomes_total": row.get("outcomes_total"),
            "pending": row.get("pending"),
            "resolved": row.get("resolved"),
            "expired": row.get("expired"),
            "expired_rate": row.get("expired_rate"),
            "fallback_total": row.get("fallback_total"),
            "fallback_pending": row.get("fallback_pending"),
            "fallback_resolved": row.get("fallback_resolved"),
            "fallback_expired": row.get("fallback_expired"),
            "fallback_expired_rate": row.get("fallback_expired_rate"),
            "generated_at": row.get("generated_at"),
            "created_at": datetime.now().isoformat(),
        }

        try:
            self.client.table("agent_outcome_health").upsert(payload, on_conflict="run_id").execute()
            return True
        except Exception as e:
            print(f"Agent Outcome Health Save Error: {e}")
            return False
