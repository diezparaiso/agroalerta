class OfflineRetryPolicy {
  const OfflineRetryPolicy._();

  static const initialDelay = Duration(seconds: 30);
  static const maxDelay = Duration(hours: 1);

  static bool isEligible(Map<String, dynamic> report, {required DateTime now}) {
    final raw = report['next_attempt_at'];
    if (raw is! String) return true;
    final nextAttempt = DateTime.tryParse(raw);
    return nextAttempt == null || !nextAttempt.isAfter(now);
  }

  static Map<String, dynamic> markFailure(
    Map<String, dynamic> report, {
    required DateTime now,
  }) {
    final attempts = (report['attempts'] as num?)?.toInt() ?? 0;
    final nextAttempts = attempts + 1;
    final multiplier = 1 << (nextAttempts - 1).clamp(0, 10);
    final delay = Duration(
      seconds: (initialDelay.inSeconds * multiplier)
          .clamp(initialDelay.inSeconds, maxDelay.inSeconds),
    );
    return {
      ...report,
      'attempts': nextAttempts,
      'last_attempt_at': now.toUtc().toIso8601String(),
      'next_attempt_at': now.add(delay).toUtc().toIso8601String(),
    };
  }

  static Map<String, dynamic> normalize(Map<String, dynamic> report) {
    return {
      ...report,
      'attempts': (report['attempts'] as num?)?.toInt() ?? 0,
      'last_attempt_at': report['last_attempt_at'],
      'next_attempt_at': report['next_attempt_at'],
    };
  }
}
