import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';

void main() {
  group('ParcelSummary', () {
    test('fromJson preserves real coordinates and parcel identity', () {
      final parcel = ParcelSummary.fromJson({
        'id': 'parcel-1',
        'label': 'Finca Norte',
        'latitude': 37.25,
        'longitude': -5.85,
        'crop_type': 'vinedo',
        'comarca': 'Campiña',
      });

      expect(parcel.id, 'parcel-1');
      expect(parcel.name, 'Finca Norte');
      expect(parcel.latitude, 37.25);
      expect(parcel.longitude, -5.85);
      expect(parcel.crop, 'Vinedo');
      expect(parcel.place, 'Campiña');
      expect(parcel.risk, 'Pendiente');
    });

    test('missing coordinates are represented as unavailable zero values', () {
      final parcel = ParcelSummary.fromJson({
        'id': 'parcel-2',
        'label': 'Finca Sur',
        'crop_type': 'olivar',
      });

      expect(parcel.latitude, 0);
      expect(parcel.longitude, 0);
      expect(parcel.crop, 'Olivar');
      expect(parcel.place, 'Andalucia');
    });

    test('toJson round-trips the parcel transport fields', () {
      const parcel = ParcelSummary(
        id: 'parcel-3',
        latitude: 37.4,
        longitude: -6.0,
        name: 'Finca Este',
        crop: 'Vinedo',
        place: 'Aljarafe',
        risk: 'Pendiente',
      );

      expect(parcel.toJson(), {
        'id': 'parcel-3',
        'label': 'Finca Este',
        'latitude': 37.4,
        'longitude': -6.0,
        'crop_type': 'vinedo',
        'comarca': 'Aljarafe',
      });
    });
  });
}
