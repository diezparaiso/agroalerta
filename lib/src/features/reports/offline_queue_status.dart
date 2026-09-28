class OfflineQueueStatus {
  const OfflineQueueStatus({
    required this.pendingCount,
    required this.failedCount,
    required this.nextAttemptAt,
  });

  final int pendingCount;
  final int failedCount;
  final DateTime? nextAttemptAt;

  bool get hasPending => pendingCount > 0;
  bool get isWaitingForRetry => nextAttemptAt != null;
}

OfflineQueueStatus summarizeOfflineQueue(
  List<Map<String, dynamic>> reports, {
  DateTime? now,
}) {
  final current = now ?? DateTime.now().toUtc();
  DateTime? nextAttempt;

  for (final report in reports) {
    final parsed = DateTime.tryParse(report['next_attempt_at'] as String? ?? '');
    if (parsed == null || !parsed.isAfter(current)) continue;
    if (nextAttempt == null || parsed.isBefore(nextAttempt)) {
      nextAttempt = parsed;
    }
  }

  return OfflineQueueStatus(
    pendingCount: reports.length,
    failedCount: reports.where((report) => (report['attempts'] as num?)?.toInt() != null && ((report['attempts'] as num?)?.toInt() ?? 0) > 0).length,
    nextAttemptAt: nextAttempt,
  );
}
