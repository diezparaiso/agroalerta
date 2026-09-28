import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final productsProvider = FutureProvider<List<ProductSummary>>((ref) async {
  try {
    final records = await ref.read(apiClientProvider).getProducts();
    return records.map(ProductSummary.fromJson).toList();
  } catch (_) {
    return const [ProductSummary(name: 'Catalogo pendiente de sincronizar', substance: 'Consultar registro oficial vigente', crop: 'Olivar · Repilo')];
  }
});

class ProductSummary {
  const ProductSummary({required this.name, required this.substance, required this.crop});

  final String name;
  final String substance;
  final String crop;

  factory ProductSummary.fromJson(Map<String, dynamic> json) => ProductSummary(
        name: json['commercial_name'] as String? ?? 'Producto sin nombre',
        substance: json['active_substance'] as String? ?? 'Sustancia no disponible',
        crop: '${json['crop_type'] ?? 'Cultivo'} · ${json['disease_code'] ?? 'Enfermedad'}',
      );
}
