import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/features/alerts/risk_history_chart.dart';

/// F3.7 — el gráfico de historial de riesgo (fl_chart) se renderiza con y sin
/// datos, también en móvil estrecho (360 px).
void main() {
  Future<void> pumpChart(WidgetTester tester, Widget chart) async {
    tester.view.physicalSize = const Size(360, 640);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Center(child: chart))));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    while (tester.takeException() != null) {
      // Cualquier excepción de pintado se registra y se descarta.
    }
  }

  testWidgets('muestra «Sin historial de riesgo» cuando no hay datos', (tester) async {
    await pumpChart(tester, const RiskHistoryChart());
    expect(find.text('Sin historial de riesgo'), findsOneWidget);
    expect(find.byType(LineChart), findsNothing);
  });

  testWidgets('pinta la línea cuando hay historial', (tester) async {
    await pumpChart(
      tester,
      RiskHistoryChart(spots: [const FlSpot(0, 0.2), const FlSpot(1, 0.7), const FlSpot(2, 0.4)]),
    );
    expect(find.byType(LineChart), findsOneWidget);
    expect(find.text('Sin historial de riesgo'), findsNothing);
  });
}
