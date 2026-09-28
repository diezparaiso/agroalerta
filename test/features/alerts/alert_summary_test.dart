import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/alerts/alerts_provider.dart';

void main() {
  group('AlertSummary', () {
    test('maps a persisted backend alert', () {
      final alert = AlertSummary.fromJson({
        'disease_code': 'repilo',
        'parcel_id': 'parcel-1',
        'risk_level': 'high',
        'risk_score': 0.82,
      });

      expect(alert.title, 'repilo');
      expect(alert.parcel, 'parcel-1');
      expect(alert.level, 'high');
      expect(alert.value, 0.82);
    });

    test('uses explicit availability-safe defaults for incomplete payloads', () {
      final alert = AlertSummary.fromJson({});

      expect(alert.title, 'Riesgo');
      expect(alert.parcel, 'Parcela');
      expect(alert.level, 'Bajo');
      expect(alert.value, 0);
    });
  });
}
