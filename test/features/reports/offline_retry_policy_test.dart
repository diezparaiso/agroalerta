import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/reports/offline_retry_policy.dart';

void main() {
  group('OfflineRetryPolicy', () {
    final base = DateTime.utc(2026, 9, 28, 10);

    test('old queue entries are immediately eligible', () {
      expect(
        OfflineRetryPolicy.isEligible({'parcel_id': 'p1'}, now: base),
        isTrue,
      );
    });

    test('future retry is not eligible yet', () {
      final report = {
        'next_attempt_at': base.add(const Duration(minutes: 5)).toIso8601String(),
      };

      expect(OfflineRetryPolicy.isEligible(report, now: base), isFalse);
      expect(
        OfflineRetryPolicy.isEligible(
          report,
          now: base.add(const Duration(minutes: 5)),
        ),
        isTrue,
      );
    });

    test('failure schedules exponential delays', () {
      final first = OfflineRetryPolicy.markFailure({}, now: base);
      final second = OfflineRetryPolicy.markFailure(first, now: base);

      expect(first['attempts'], 1);
      expect(first['next_attempt_at'], base.add(const Duration(seconds: 30)).toIso8601String());
      expect(second['attempts'], 2);
      expect(second['next_attempt_at'], base.add(const Duration(minutes: 1)).toIso8601String());
    });

    test('backoff is capped at one hour', () {
      Map<String, dynamic> report = {};
      for (var i = 0; i < 20; i++) {
        report = OfflineRetryPolicy.markFailure(report, now: base);
      }

      expect(report['attempts'], 20);
      expect(
        report['next_attempt_at'],
        base.add(const Duration(hours: 1)).toIso8601String(),
      );
    });

    test('legacy reports receive retry defaults', () {
      final normalized = OfflineRetryPolicy.normalize({'parcel_id': 'p1'});

      expect(normalized['attempts'], 0);
      expect(normalized.containsKey('next_attempt_at'), isTrue);
    });
  });
}
