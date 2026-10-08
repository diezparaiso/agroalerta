import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/offline_cache.dart';
import '../parcels/parcel_provider.dart';
import '../settings/preferences_store.dart';

/// Clima de la primera parcela con **caché local** (F3.6): la respuesta se
/// guarda en SharedPreferences y, si la petición falla y la preferencia
/// «Mostrar datos en caché» está activada, se devuelve la última copia
/// marcada con `cached: true`. Así se evitan llamadas repetidas a la API
/// (el backend además cachea aemet/ria) y la app sigue siendo útil sin red.
final weatherProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final parcels = await ref.watch(parcelsProvider.future);
  final id = parcels.isEmpty ? null : parcels.first.id;
  if (id == null) {
    throw StateError('No hay parcelas consultables para obtener clima real');
  }
  final cache = OfflineCache();
  final cacheKey = 'weather:$id';
  try {
    final weather = await ref.read(apiClientProvider).getWeather(id);
    await cache.save(cacheKey, weather);
    return weather;
  } catch (error) {
    final cachedEnabled = await PreferencesStore().offlineCacheEnabled();
    if (cachedEnabled) {
      final cached = await cache.read(cacheKey);
      if (cached is Map<String, dynamic>) {
        return {...cached, 'cached': true};
      }
    }
    rethrow;
  }
});
