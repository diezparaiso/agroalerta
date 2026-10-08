import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:agroalerta_andalucia/src/core/network/api_client.dart';
import 'package:agroalerta_andalucia/src/features/home/weather_provider.dart';
import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';

/// Cliente simulado: sin red real (F3.3).
class _FakeApiClient extends ApiClient {
  _FakeApiClient({required this.weather, this.fail = false}) : super(baseUrl: 'http://localhost:0');

  final Map<String, dynamic> weather;
  final bool fail;

  @override
  Future<Map<String, dynamic>> getWeather(String parcelId) async {
    if (fail) throw StateError('sin conexión');
    return weather;
  }
}

ParcelSummary _parcel() => const ParcelSummary(
      id: 'p1',
      name: 'Olivar norte',
      crop: 'Olivar',
      place: 'Sevilla',
      risk: 'bajo',
    );

ProviderContainer _container({required ApiClient client}) => ProviderContainer(
      overrides: [
        parcelsProvider.overrideWith((ref) async => [_parcel()]),
        apiClientProvider.overrideWithValue(client),
      ],
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('guarda el clima en caché cuando la consulta funciona', () async {
    SharedPreferences.setMockInitialValues({});
    final container = _container(
      client: _FakeApiClient(weather: {'temperature_c': 21.5, 'source': 'aemet'}),
    );
    addTearDown(container.dispose);

    final weather = await container.read(weatherProvider.future);

    expect(weather['temperature_c'], 21.5);
    final preferences = await SharedPreferences.getInstance();
    final cached = preferences.getString('weather:p1');
    expect(cached, isNotNull);
    expect(cached, contains('temperature_c'));
  });

  test('sin conexión devuelve la última caché marcada como caché', () async {
    SharedPreferences.setMockInitialValues({
      'weather:p1': '{"temperature_c":19.5,"source":"aemet"}',
    });
    final container = _container(client: _FakeApiClient(weather: const {}, fail: true));
    addTearDown(container.dispose);

    final weather = await container.read(weatherProvider.future);

    expect(weather['temperature_c'], 19.5);
    expect(weather['cached'], isTrue);
  });

  test('con la preferencia de caché desactivada el error se propaga', () async {
    SharedPreferences.setMockInitialValues({
      'agroalerta.offline': false,
      'weather:p1': '{"temperature_c":19.5}',
    });
    final container = _container(client: _FakeApiClient(weather: const {}, fail: true));
    addTearDown(container.dispose);

    await expectLater(container.read(weatherProvider.future), throwsStateError);
  });

  test('sin conexión y sin caché el error se propaga', () async {
    SharedPreferences.setMockInitialValues({});
    final container = _container(client: _FakeApiClient(weather: const {}, fail: true));
    addTearDown(container.dispose);

    await expectLater(container.read(weatherProvider.future), throwsStateError);
  });
}
