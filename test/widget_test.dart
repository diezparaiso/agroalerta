import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:agroalerta_andalucia/src/app.dart';

void main() {
  testWidgets('AgroAlerta inicia correctamente', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: AgroAlertaApp()));
    await tester.pump();
  });
}
