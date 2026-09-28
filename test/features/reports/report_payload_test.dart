import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';
import 'package:agroalerta_andalucia/src/features/reports/report_payload.dart';

void main() {
  group('buildFieldReportPayload', () {
    test('uses the selected parcel identity and real coordinates', () {
      const parcel = ParcelSummary(
        id: 'parcel-7',
        latitude: 37.31,
        longitude: -5.91,
        name: 'Finca Norte',
        crop: 'Olivar',
        place: 'Sevilla',
        risk: 'Pendiente',
      );

      final payload = buildFieldReportPayload(
        parcel: parcel,
        type: 'sintoma',
        notes: 'Manchas en hojas',
        count: 4,
        photoUrl: 'https://example.invalid/photo.jpg',
      );

      expect(payload['parcel_id'], 'parcel-7');
      expect(payload['latitude'], 37.31);
      expect(payload['longitude'], -5.91);
      expect(payload['type'], 'sintoma');
      expect(payload['count'], 4);
      expect(payload['photo_url'], 'https://example.invalid/photo.jpg');
      expect(payload['reported_at'], isA<String>());
    });

    test('rejects a parcel without persistent identity or coordinates', () {
      const parcel = ParcelSummary(
        id: null,
        name: 'Parcela incompleta',
        crop: 'Olivar',
        place: 'Sevilla',
        risk: 'Pendiente',
      );

      expect(
        () => buildFieldReportPayload(
          parcel: parcel,
          type: 'sintoma',
          notes: '',
          count: 0,
          photoUrl: null,
        ),
        throwsArgumentError,
      );
    });
  });
}
