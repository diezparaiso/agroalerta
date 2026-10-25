import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';

void main() {
  test('fromJson convierte los campos reales del backend', () {
    final parcel = ParcelSummary.fromJson({
      'id': 'p1',
      'label': 'Olivar norte',
      'latitude': 37.4,
      'longitude': -5.9,
      'crop_type': 'olivar',
      'comarca': 'Campiña de Sevilla',
    });

    expect(parcel.id, 'p1');
    expect(parcel.name, 'Olivar norte');
    expect(parcel.crop, 'Olivar');
    expect(parcel.place, 'Campiña de Sevilla');
    expect(parcel.latitude, 37.4);
    expect(parcel.longitude, -5.9);
  });

  test('sin coordenadas en el backend quedan null: nunca se inventan', () {
    final parcel = ParcelSummary.fromJson({
      'id': 'p2',
      'label': 'Viñedo sur',
      'crop_type': 'vinedo',
    });

    expect(parcel.latitude, isNull);
    expect(parcel.longitude, isNull);
    expect(parcel.crop, 'Viñedo');
  });

  test('toJson conserva las coordenadas reales en la caché local', () {
    const parcel = ParcelSummary(
      latitude: 37.1,
      longitude: -6.2,
      name: 'Parcela de prueba',
      crop: 'Olivar',
      place: 'Huelva',
      risk: 'Pendiente',
    );

    final restored = ParcelSummary.fromJson(parcel.toJson());

    expect(restored.latitude, 37.1);
    expect(restored.longitude, -6.2);
    expect(restored.name, 'Parcela de prueba');
    expect(restored.crop, 'Olivar');
  });
}
