import 'package:flutter/material.dart';

import 'profile_store.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({required this.userId, required this.onComplete, super.key});

  final String userId;
  final VoidCallback onComplete;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final comarcaController = TextEditingController();
  final crops = <String>{};

  @override
  void dispose() {
    comarcaController.dispose();
    super.dispose();
  }

  Future<void> save() async {
    await ProfileStore().save(widget.userId, comarcaController.text.trim(), crops);
    widget.onComplete();
  }

  @override
  Widget build(BuildContext context) {
    final valid = comarcaController.text.trim().isNotEmpty && crops.isNotEmpty;
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  Text('Configura tus avisos', style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  const Text('Usaremos estos datos para priorizar riesgos en tus parcelas.'),
                  const SizedBox(height: 22),
                  TextField(controller: comarcaController, onChanged: (_) => setState(() {}), decoration: const InputDecoration(labelText: 'Comarca o municipio')),
                  const SizedBox(height: 18),
                  const Text('Cultivos de interés'),
                  CheckboxListTile(value: crops.contains('olivar'), title: const Text('Olivar'), onChanged: (value) => setState(() => value == true ? crops.add('olivar') : crops.remove('olivar'))),
                  CheckboxListTile(value: crops.contains('vinedo'), title: const Text('Viñedo'), onChanged: (value) => setState(() => value == true ? crops.add('vinedo') : crops.remove('vinedo'))),
                  const SizedBox(height: 18),
                  FilledButton(onPressed: valid ? save : null, child: const Text('Continuar')),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
