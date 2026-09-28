import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../home/home_screen.dart';
import 'products_provider.dart';

class ProductsScreen extends ConsumerWidget {
  const ProductsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => AppPage(title: 'Productos autorizados', subtitle: 'Consulta el catalogo sincronizado del MAPA', child: ref.watch(productsProvider(const ProductFilter())).when(data: (products) {
      if (products.isEmpty) return const Center(child: Text('Catálogo MAPA no disponible.'));
      return ListView(children: [for (final product in products) _ProductTile(name: product.name, substance: product.substance, crop: product.crop, dose: product.dose, safetyPeriodDays: product.safetyPeriodDays)]);
    }, loading: () => const Center(child: CircularProgressIndicator()), error: (error, stack) => Center(child: Text('No se pudo cargar el catalogo: $error'))));
}

class _ProductTile extends StatelessWidget {
  const _ProductTile({required this.name, required this.substance, required this.crop, required this.dose, required this.safetyPeriodDays});
  final String name, substance, crop, dose;
  final int safetyPeriodDays;
  @override
  Widget build(BuildContext context) => Card(child: ListTile(contentPadding: const EdgeInsets.all(18), leading: const Icon(Icons.inventory_2_outlined, size: 32), title: Text(name, style: const TextStyle(fontWeight: FontWeight.w700)), subtitle: Text('$crop\n$substance\nDosis registrada: $dose\nPlazo de seguridad: $safetyPeriodDays días\n\nComprueba siempre la etiqueta y autorización vigente.'), isThreeLine: true));
}
