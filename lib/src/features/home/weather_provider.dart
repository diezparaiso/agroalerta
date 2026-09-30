import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final weatherProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final parcels = await ref.watch(parcelsProvider.future);
  final id = parcels.isEmpty ? null : parcels.first.id;
  if (id == null) {
    throw StateError('No hay parcelas consultables para obtener clima real');
  }
  return await ref.read(apiClientProvider).getWeather(id);
});
