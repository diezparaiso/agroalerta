import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final productsProvider = FutureProvider.family<List<ProductSummary>, ProductFilter>((ref, filter) async {
  try {
    final records = await ref.read(apiClientProvider).getProducts(
          cropType: filter.cropType,
          diseaseCode: filter.diseaseCode,
        );
    return records.map(ProductSummary.fromJson).toList();
  } catch (_) {
    return const [];
  }
});

class ProductSummary {
  const ProductSummary({required this.name, required this.substance, required this.crop, required this.dose, required this.safetyPeriodDays});

  final String name;
  final String substance;
  final String crop;
  final String dose;
  final int safetyPeriodDays;

  factory ProductSummary.fromJson(Map<String, dynamic> json) => ProductSummary(
        name: json['commercial_name'] as String? ?? 'Producto sin nombre',
        substance: json['active_substance'] as String? ?? 'Sustancia no disponible',
        crop: '${json['crop_type'] ?? 'Cultivo'} · ${json['disease_code'] ?? 'Enfermedad'}',
        dose: json['dose'] as String? ?? 'No disponible',
        safetyPeriodDays: (json['safety_period_days'] as num?)?.toInt() ?? 0,
      );
}


class ProductFilter {
  const ProductFilter({this.cropType, this.diseaseCode});
  final String? cropType;
  final String? diseaseCode;
}
