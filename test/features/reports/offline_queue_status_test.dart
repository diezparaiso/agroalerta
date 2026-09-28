import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/reports/offline_queue_status.dart';

void main() {
  test('summarizes pending and failed reports', () {
    final now = DateTime.utc(2026, 9, 28, 10);
    final status = summarizeOfflineQueue([
      {'parcel_id': 'p1', 'attempts': 0},
      {
        'parcel_id': 'p2',
        'attempts': 2,
        'next_attempt_at': now.add(const Duration(minutes: 10)).toIso8601String(),
      },
    ], now: now);

    expect(status.pendingCount, 2);
    expect(status.failedCount, 1);
    expect(status.nextAttemptAt, now.add(const Duration(minutes: 10)));
  });

  test('reports no waiting retry when all pending entries are eligible', () {
    final now = DateTime.utc(2026, 9, 28, 10);
    final status = summarizeOfflineQueue([
      {'attempts': 0},
      {'attempts': 1, 'next_attempt_at': now.subtract(const Duration(minutes: 1)).toIso8601String()},
    ], now: now);

    expect(status.pendingCount, 2);
    expect(status.failedCount, 1);
    expect(status.nextAttemptAt, isNull);
  });

  test('empty queue has no pending status', () {
    final status = summarizeOfflineQueue(const []);

    expect(status.pendingCount, 0);
    expect(status.failedCount, 0);
    expect(status.hasPending, isFalse);
  });
}
