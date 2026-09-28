import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final weatherProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    final parcels = await ref.watch(parcelsProvider.future);
    final id = parcels.isEmpty ? null : parcels.first.id;
    if (id == null) return const {'temperature_c': 18.4, 'relative_humidity': 87, 'rainfall_mm_24h': 12.2, 'source': 'estimado'};
    return await ref.read(apiClientProvider).getWeather(id);
  } catch (_) {
    return const {'temperature_c': 18.4, 'relative_humidity': 87, 'rainfall_mm_24h': 12.2, 'source': 'estimado'};
  }
});
