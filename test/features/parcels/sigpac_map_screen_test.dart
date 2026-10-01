import 'package:agroalerta_andalucia/src/features/parcels/sigpac_map_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('muestra los controles de consulta SIGPAC', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: SigpacMapScreen()),
      ),
    );

    expect(find.text('Importar recintos SIGPAC'), findsOneWidget);
    expect(find.text('Oeste'), findsOneWidget);
    expect(find.text('Sur'), findsOneWidget);
    expect(find.text('Este'), findsOneWidget);
    expect(find.text('Norte'), findsOneWidget);
    expect(find.text('Buscar recintos'), findsOneWidget);
    expect(find.text('Importar área'), findsOneWidget);
  });
}
