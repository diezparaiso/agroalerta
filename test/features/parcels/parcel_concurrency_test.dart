import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/core/network/api_client.dart';

import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';

void main() {
  test('ParcelSummary preserves server updated_at for conflict protection', () {
    final parcel = ParcelSummary.fromJson({
      'id': 'parcel-1',
      'label': 'Finca Norte',
      'latitude': 37.3,
      'longitude': -5.9,
      'crop_type': 'olivar',
      'comarca': 'Campiña',
      'updated_at': '2026-09-28T10:00:00Z',
    });

    expect(parcel.updatedAt, DateTime.utc(2026, 9, 28, 10));
    expect(parcel.toJson()['updated_at'], '2026-09-28T10:00:00.000Z');
  });

  test('parcel without server version cannot be updated safely', () async {
    const parcel = ParcelSummary(
      id: 'parcel-1',
      name: 'Finca Norte',
      crop: 'Olivar',
      place: 'Campiña',
      risk: 'Pendiente',
    );

    expect(
      () => updateParcelWithConflictProtection(
        apiClient: ApiClient(),
        parcel: parcel,
        label: 'Nueva finca',
      ),
      throwsStateError,
    );
  });
}
