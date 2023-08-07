from datetime import datetime, timedelta

from django.conf import settings

from sentry.utils import redis

BUFFER_SIZE = 30  # 30 days
KEY_EXPIRY = 60 * 60 * 24 * 30  # 30 days

BROKEN_RANGE_DAYS = 7  # 7 days

VALID_KEYS = ["success", "error", "fatal"]


class IntegrationRequestBuffer:
    """
    Create a data structure to store daily successful and failed request counts for each installed integration in Redis
    This should store the aggregate counts of each type for last 30 days for each integration
    """

    def __init__(self, key, expiration_seconds=KEY_EXPIRY):
        cluster_id = settings.SENTRY_INTEGRATION_ERROR_LOG_REDIS_CLUSTER
        self.client = redis.redis_clusters.get(cluster_id)
        self.integration_key = key
        self.key_expiration_seconds = expiration_seconds

    def record_error(self):
        self._add("error")

    def record_success(self):
        self._add("success")

    def record_fatal(self):
        self._add("fatal")

    def is_integration_broken(self):
        """
        Integration is broken if we have 7 consecutive days of errors and no successes OR have a fatal error

        """
        broken_range_days_counts = self._get_broken_range_from_buffer()

        days_fatal = []
        days_error = []

        for day_count in broken_range_days_counts:
            if int(day_count.get("fatal_count", 0)) > 0:
                days_fatal.append(day_count)
            elif (
                int(day_count.get("error_count", 0)) > 0
                and int(day_count.get("success_count", 0)) == 0
            ):
                days_error.append(day_count)

        if len(days_fatal) > 0:
            return True

        if not len(days_error):
            return False

        if len(days_error) < BROKEN_RANGE_DAYS:
            return False

        return True

    def _add(self, count: str):
        if count not in VALID_KEYS:
            raise Exception("Requires a valid key param.")

        now = datetime.now().strftime("%Y-%m-%d")
        buffer_key = f"{self.integration_key}:{now}"

        pipe = self.client.pipeline()
        pipe.hincrby(buffer_key, count + "_count", 1)
        pipe.expire(buffer_key, self.key_expiration_seconds)
        pipe.execute()

    def _get_all_from_buffer(self):
        """
        Get the list at the buffer key.
        """

        now = datetime.now()
        all_range = [
            f"{self.integration_key}:{(now - timedelta(days=i)).strftime('%Y-%m-%d')}"
            for i in range(BUFFER_SIZE)
        ]

        return self._get_range_buffers(all_range)

    def _get_broken_range_from_buffer(self):
        """
        Get the list at the buffer key in the broken range.
        """

        now = datetime.now()
        broken_range_keys = [
            f"{self.integration_key}:{(now - timedelta(days=i)).strftime('%Y-%m-%d')}"
            for i in range(BROKEN_RANGE_DAYS)
        ]

        return self._get_range_buffers(broken_range_keys)

    def _get_range_buffers(self, keys):
        pipe = self.client.pipeline()
        ret = []
        for key in keys:
            pipe.hgetall(key)
        response = pipe.execute()
        for item in response:
            ret.append(item)

        return ret
