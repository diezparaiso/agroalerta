import 'package:flutter_test/flutter_test.dart';
import 'package:agroalerta_andalucia/src/features/products/products_provider.dart';

void main() {
  test('maps MAPA safety metadata without inventing values', () {
    final product = ProductSummary.fromJson({
      'commercial_name': 'Producto autorizado',
      'active_substance': 'Sustancia activa',
      'crop_type': 'olivar',
      'disease_code': 'repilo',
      'dose': '1.5 L/ha',
      'safety_period_days': 21,
    });

    expect(product.name, 'Producto autorizado');
    expect(product.dose, '1.5 L/ha');
    expect(product.safetyPeriodDays, 21);
  });

  test('uses explicit unavailable values when catalog metadata is absent', () {
    final product = ProductSummary.fromJson({});

    expect(product.dose, 'No disponible');
    expect(product.safetyPeriodDays, 0);
  });
}
