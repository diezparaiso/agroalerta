import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/offline_cache.dart';
import '../parcels/parcel_provider.dart';

const _weatherCachePrefix = 'agroalerta.weather.v1.';

final weatherProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final parcels = await ref.watch(parcelsProvider.future);
  final id = parcels.isEmpty ? null : parcels.first.id;
  if (id == null) {
    return const {'status': 'no_parcel'};
  }

  final cache = OfflineCache();
  final cacheKey = '$_weatherCachePrefix$id';
  try {
    final result = await ref.read(apiClientProvider).getWeather(id);
    await cache.save(cacheKey, {
      'saved_at': DateTime.now().toUtc().toIso8601String(),
      'data': result,
    });
    return {...result, '_cache_status': 'fresh'};
  } catch (_) {
    final cached = await cache.read(cacheKey);
    if (cached is Map && cached['data'] is Map) {
      return {
        ...(cached['data'] as Map).cast<String, dynamic>(),
        '_cache_status': 'stale',
        '_cached_at': cached['saved_at']?.toString(),
      };
    }
    rethrow;
  }
});
