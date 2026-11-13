/// Enderecos das 3 agencias. Conta N pertence a agencia N % 3 (mesma regra do
/// backend, ver agencia/src/config.py).
///
/// Para trocar o host (ex.: emulador Android usa 10.0.2.2):
///   flutter run --dart-define=AGENCIA_HOST=10.0.2.2
const String agenciaHost = String.fromEnvironment('AGENCIA_HOST', defaultValue: 'localhost');
const int portaBase = int.fromEnvironment('PORTA_BASE', defaultValue: 4000);
const int numeroAgencias = 3;

List<String> urlsPadrao() => [
      for (var i = 0; i < numeroAgencias; i++) 'http://$agenciaHost:${portaBase + i}',
    ];

int agenciaDaConta(int idConta) => idConta % numeroAgencias;
