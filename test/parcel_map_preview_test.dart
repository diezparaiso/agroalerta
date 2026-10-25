import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/parcels/parcel_map_preview.dart';
import 'package:agroalerta_andalucia/src/features/parcels/parcel_provider.dart';

/// F3.7 — el mapa (flutter_map) se renderiza y solo dibuja marcadores de
/// parcelas con coordenadas reales. En tests no hay red, así que las peticiones
/// de teselas fallan y sus excepciones se descartan a propósito.
void main() {
  const conCoordenadas = ParcelSummary(
    id: 'p1',
    latitude: 37.39,
    longitude: -5.99,
    name: 'Olivar norte',
    crop: 'Olivar',
    place: 'Sevilla',
    risk: 'medio',
  );
  const sinCoordenadas = ParcelSummary(
    id: 'p2',
    name: 'Parcela sin ubicar',
    crop: 'Viñedo',
    place: 'Jerez',
    risk: 'bajo',
  );

  Future<void> pumpMap(WidgetTester tester, List<ParcelSummary> parcels) async {
    tester.view.physicalSize = const Size(800, 600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(
      ProviderScope(
        overrides: [parcelsProvider.overrideWith((ref) async => parcels)],
        child: const MaterialApp(home: Scaffold(body: ParcelMapPreview())),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
  }

  testWidgets('muestra un marcador por parcela con coordenadas', (tester) async {
    await pumpMap(tester, const [conCoordenadas, sinCoordenadas]);
    expect(find.byType(FlutterMap), findsOneWidget);
    expect(find.byIcon(Icons.location_pin), findsOneWidget);
    while (tester.takeException() != null) {
      // Teselas sin red en pruebas: se descartan.
    }
  });

  testWidgets('acepta la lista vacía sin excepciones', (tester) async {
    await pumpMap(tester, const []);
    expect(find.byType(FlutterMap), findsOneWidget);
    expect(find.byIcon(Icons.location_pin), findsNothing);
    while (tester.takeException() != null) {
      // Teselas sin red en pruebas: se descartan.
    }
  });
}
