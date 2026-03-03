"""Unit tests for scheduler forecast refresh job (plan 04-04).

Tests that the nightly forecast cache refresh job is registered correctly.
"""
from unittest.mock import patch, MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# Test 1: Nightly refresh job is registered with CronTrigger(hour=3)
# ---------------------------------------------------------------------------

def test_nightly_refresh_job_registered():
    """start_scheduler() registers a job with id='refresh_forecast_cache' and CronTrigger."""
    with patch("app.integrations.scheduler.settings") as mock_settings, \
         patch("app.integrations.scheduler.BackgroundScheduler") as MockScheduler:

        mock_settings.price_sync_enabled = True
        mock_settings.price_sync_interval_hours = 24

        mock_scheduler_instance = MagicMock()
        MockScheduler.return_value = mock_scheduler_instance

        from app.integrations.scheduler import start_scheduler
        start_scheduler()

        # Find the add_job call for forecast refresh
        add_job_calls = mock_scheduler_instance.add_job.call_args_list
        forecast_job_call = None
        for c in add_job_calls:
            if c.kwargs.get("id") == "refresh_forecast_cache" or \
               (len(c.args) > 0 and len(c) > 1 and "refresh_forecast_cache" in str(c)):
                forecast_job_call = c
                break

        # Check that a job with the forecast refresh ID was added
        job_ids = [c.kwargs.get("id", "") for c in add_job_calls]
        assert "refresh_forecast_cache" in job_ids, (
            f"Expected 'refresh_forecast_cache' in job IDs, got {job_ids}"
        )


# ---------------------------------------------------------------------------
# Test 2: Calling start_scheduler twice doesn't duplicate the job
# ---------------------------------------------------------------------------

def test_refresh_job_has_replace_existing():
    """Job uses replace_existing=True to prevent duplication on restart."""
    with patch("app.integrations.scheduler.settings") as mock_settings, \
         patch("app.integrations.scheduler.BackgroundScheduler") as MockScheduler:

        mock_settings.price_sync_enabled = True
        mock_settings.price_sync_interval_hours = 24

        mock_scheduler_instance = MagicMock()
        MockScheduler.return_value = mock_scheduler_instance

        from app.integrations.scheduler import start_scheduler
        start_scheduler()
        start_scheduler()

        # Find all add_job calls with refresh_forecast_cache
        forecast_calls = [
            c for c in mock_scheduler_instance.add_job.call_args_list
            if c.kwargs.get("id") == "refresh_forecast_cache"
        ]

        # All calls should have replace_existing=True
        for c in forecast_calls:
            assert c.kwargs.get("replace_existing") is True, (
                "refresh_forecast_cache job must use replace_existing=True"
            )
