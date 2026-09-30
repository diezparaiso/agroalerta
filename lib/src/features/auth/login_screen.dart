import 'package:flutter/material.dart';

import 'auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({required this.authService, required this.firebaseAvailable, super.key});

  final AuthService? authService;
  final bool firebaseAvailable;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final emailController = TextEditingController();
  final passwordController = TextEditingController();
  bool loading = false;
  String? error;

  @override
  void dispose() {
    emailController.dispose();
    passwordController.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      await action();
    } catch (_) {
      if (mounted) setState(() => error = 'No se pudo completar la operacion. Revisa tus datos.');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final enabled = widget.firebaseAvailable && !loading;
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 460),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Icon(Icons.eco, size: 52),
                  const SizedBox(height: 20),
                  Text('AgroAlerta Andalucia', style: Theme.of(context).textTheme.headlineSmall, textAlign: TextAlign.center),
                  const SizedBox(height: 8),
                  const Text('Inicia sesion para proteger tus parcelas', textAlign: TextAlign.center),
                  const SizedBox(height: 28),
                  FilledButton.icon(onPressed: enabled ? () => _run(() async { await widget.authService!.signInWithGoogle(); }) : null, icon: const Icon(Icons.account_circle_outlined), label: const Text('Continuar con Google')),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(onPressed: enabled ? () => _run(() async { await widget.authService!.signInWithApple(); }) : null, icon: const Icon(Icons.apple), label: const Text('Continuar con Apple')),
                  const SizedBox(height: 22),
                  TextField(controller: emailController, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Correo electronico')),
                  const SizedBox(height: 12),
                  TextField(controller: passwordController, obscureText: true, decoration: const InputDecoration(labelText: 'Contrasena')),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: enabled ? () => _run(() async { await widget.authService!.signInWithEmail(emailController.text.trim(), passwordController.text); }) : null, child: const Text('Entrar')),
                  OutlinedButton(onPressed: enabled ? () => _run(() async { await widget.authService!.createAccount(emailController.text.trim(), passwordController.text); }) : null, child: const Text('Crear cuenta')),
                  TextButton(onPressed: enabled ? () => _run(() async { await widget.authService!.sendPasswordReset(emailController.text.trim()); }) : null, child: const Text('He olvidado mi contrasena')),
                  if (error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error), textAlign: TextAlign.center)),
                  if (!widget.firebaseAvailable) const Padding(padding: EdgeInsets.only(top: 16), child: Text('Configura Firebase para activar el acceso.', textAlign: TextAlign.center)),
                ])),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
