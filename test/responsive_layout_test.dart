import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/alerts/alerts_provider.dart';
import 'package:agroalerta_andalucia/src/features/alerts/alerts_screen.dart';
import 'package:agroalerta_andalucia/src/features/home/home_screen.dart';
import 'package:agroalerta_andalucia/src/features/home/telemetry_provider.dart';
import 'package:agroalerta_andalucia/src/features/home/weather_provider.dart';
import 'package:agroalerta_andalucia/src/features/irrigation/irrigation_screen.dart';
import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';
import 'package:agroalerta_andalucia/src/features/parcels/parcels_screen.dart';
import 'package:agroalerta_andalucia/src/features/reports/report_screen.dart';

/// F3.2 — comprobaciones responsive en tres tamaños reales. Los datos son
/// simulados (sin red) y solo se falla si hay **desbordamientos de
/// maquetación**; otras excepciones esperables en tests (p. ej. la carga de
/// teselas del mapa, que en pruebas devuelve HTTP 400) se descartan.
void main() {
  const sizes = <String, Size>{
    'móvil 360x640': Size(360, 640),
    'tablet 768x1024': Size(768, 1024),
    'escritorio 1280x800': Size(1280, 800),
  };

  final parcels = [
    const ParcelSummary(
      id: 'p1',
      latitude: 37.39,
      longitude: -5.99,
      name: 'Olivar norte',
      crop: 'Olivar',
      place: 'Campiña de Sevilla',
      risk: 'medio',
    ),
    const ParcelSummary(
      id: 'p2',
      latitude: 37.45,
      longitude: -6.1,
      name: 'Viñedo sur',
      crop: 'Viñedo',
      place: 'Marco de Jerez',
      risk: 'bajo',
    ),
  ];

  List<Override> overrides() => [
        parcelsProvider.overrideWith((ref) async => parcels),
        alertsProvider.overrideWith((ref) async => [
              const AlertSummary(
                title: 'Repilo',
                parcelId: 'p1',
                parcel: 'Olivar norte',
                level: 'alto',
                value: 0.82,
              ),
            ]),
        weatherProvider.overrideWith((ref) async => {
              'temperature_c': 21.5,
              'relative_humidity': 68,
              'rainfall_mm_24h': 0.4,
              'source': 'ria-ifapa',
            }),
        telemetryProvider.overrideWith((ref) async => null),
      ];

  /// Saca todas las excepciones registradas y devuelve solo las de maquetación.
  List<String> takeOverflowErrors(WidgetTester tester) {
    final overflows = <String>[];
    Object? exception;
    while ((exception = tester.takeException()) != null) {
      final message = exception.toString();
      if (message.contains('overflowed')) overflows.add(message);
    }
    return overflows;
  }

  /// Pinta [screen] en [size] y devuelve los desbordamientos detectados.
  Future<List<String>> pumpAt(WidgetTester tester, Size size, Widget screen) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: overrides(),
        child: MaterialApp(home: Scaffold(body: screen)),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 60));
    final overflows = takeOverflowErrors(tester);
    // Última pasada para descartar excepciones asíncronas llegadas tarde.
    await tester.pump();
    overflows.addAll(takeOverflowErrors(tester));
    return overflows;
  }

  final screens = <String, Widget Function()>{
    'inicio': () => const HomeScreen(),
    'parcelas': () => const ParcelsScreen(),
    'avisos': () => const AlertsScreen(),
    'observación': () => const ReportScreen(),
    'riego': () => const IrrigationScreen(),
  };

  for (final entry in screens.entries) {
    for (final size in sizes.entries) {
      testWidgets(
        '${entry.key} sin desbordamientos en ${size.key}',
        (tester) async {
          final overflows = await pumpAt(tester, size.value, entry.value());
          expect(overflows, isEmpty,
              reason: 'Desbordamientos en ${entry.key} a ${size.key}: $overflows');
          await tester.pump();
          takeOverflowErrors(tester);
        },
        timeout: const Timeout(Duration(minutes: 2)),
      );
    }
  }
}
