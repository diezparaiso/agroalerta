import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../home/home_screen.dart';
import 'products_provider.dart';

class ProductsScreen extends ConsumerWidget {
  const ProductsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AppPage(
      title: 'Productos autorizados',
      subtitle: 'Consulta el catalogo sincronizado del MAPA',
      child: ref.watch(productsProvider).when(
            data: (products) => ListView(
              children: [
                for (final product in products)
                  _ProductTile(
                    name: product.name,
                    substance: product.substance,
                    crop: product.crop,
                  ),
              ],
            ),
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, _) => Center(
              child: Text('No se pudo cargar el catalogo: $error'),
            ),
          ),
    );
  }
}

class _ProductTile extends StatelessWidget {
  const _ProductTile({
    required this.name,
    required this.substance,
    required this.crop,
  });

  final String name;
  final String substance;
  final String crop;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(18),
        leading: const Icon(Icons.inventory_2_outlined, size: 32),
        title: Text(
          name,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        subtitle: Text(
          crop +
              '\n' +
              substance +
              '\n\nComprueba siempre la etiqueta y autorizacion vigente.',
        ),
        isThreeLine: true,
      ),
    );
  }
}
