using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

// Nivel 9 del plan de validación: la biblioteca que genera el compilador, usada desde Unity,
// da los mismos estados y atributos que la máquina de código de tres direcciones (la traza
// está en Resources/pixellang.json), cada instancia de un personaje tiene su propia ficha, las
// escenas muestran esos estados y el minijuego solo envía eventos: lo que pasa con ellos lo
// decide la biblioteca.
// Se ejecutan con: unity test <proyecto> --mode PlayMode
public class PruebasPixelLang
{
    [Test]
    public void LaBibliotecaDaLaMismaTrazaQueElTAC()
    {
        var mapa = MapaPixelLang.Cargar();
        Assert.AreEqual(2, mapa.simulaciones.Length, "ejemplos/juego.pxl tiene dos bloques simular");
        foreach (var simulacion in mapa.simulaciones)
        {
            var personaje = new PersonajeNativo(mapa.personajes[simulacion.personaje]);
            for (int i = 0; i < simulacion.pasos.Length; i++)
            {
                var paso = simulacion.pasos[i];
                if (i == 0)
                    personaje.Iniciar();
                else
                    personaje.Enviar(paso.evento);
                Assert.IsTrue(personaje.Coincide(paso),
                    $"{personaje.datos.nombre}, paso {i} ({paso.evento}): la máquina de TAC da {paso.estado} y la biblioteca, {personaje.Estado}");
            }
        }
    }

    [Test]
    public void LaBibliotecaRechazaIndicesInvalidos()
    {
        var mapa = MapaPixelLang.Cargar();
        Assert.AreEqual(64, mapa.instancias_por_personaje);
        int total = mapa.personajes.Length * mapa.instancias_por_personaje;    // 2 · 64 = 128
        Assert.AreEqual(3, PixelLangNative.pl_iniciar(-1));
        Assert.AreEqual(3, PixelLangNative.pl_iniciar(total));
        Assert.AreEqual(3, PixelLangNative.pl_evento(0, 999));
        Assert.AreEqual(-1, PixelLangNative.pl_estado(total));
        Assert.AreEqual(0, PixelLangNative.pl_iniciar(total - 1), "la última instancia del último personaje");
    }

    [Test]
    public void CadaSlimeTieneSuPropiaFicha()
    {
        var mapa = MapaPixelLang.Cargar();
        var datos = mapa.Personaje("Slime");
        var primero = new ActorPixelLang(datos, mapa.Instancia(datos, 0));
        var segundo = new ActorPixelLang(datos, mapa.Instancia(datos, 1));
        Assert.AreEqual(1, primero.Instancia);
        Assert.AreEqual(3, segundo.Instancia, "instancia 1 del personaje 1: 1 + 2·1");
        primero.Iniciar(0f);
        segundo.Iniciar(0f);
        segundo.Enviar("recibir_golpe", 0f);                  // solo el segundo: Aturdido, vida 20
        Assert.AreEqual("Patrulla", primero.Estado);
        Assert.AreEqual(30, (int)primero.Valor("vida"));
        Assert.AreEqual("Aturdido", segundo.Estado);
        Assert.AreEqual(20, (int)segundo.Valor("vida"));
        primero.Enviar("ver_jugador", 0f);                    // y ahora solo el primero
        Assert.AreEqual("Persecucion", primero.Estado);
        Assert.AreEqual("Aturdido", segundo.Estado);
    }

    [Test]
    public void AturdidoElCaballeroIgnoraAtacar()
    {
        var caballero = new ActorPixelLang(MapaPixelLang.Cargar().Personaje("Caballero"));
        caballero.Iniciar(0f);
        Assert.AreEqual("Reposo", caballero.Estado);
        Assert.GreaterOrEqual(caballero.Enviar("recibir_golpe", 0f), 0);
        Assert.AreEqual("Aturdido", caballero.Estado);
        Assert.AreEqual(-1, caballero.Enviar("atacar", 0f), "Aturdido no tiene una transición con atacar");
        Assert.AreEqual("Aturdido", caballero.Estado);
        Assert.AreEqual(75, (int)caballero.Valor("vida"));
        StringAssert.Contains("no tiene esa transición", caballero.Ignorado);
    }

    [Test]
    public void LaGuardaLlevaAlSlimeASuEstadoFinal()
    {
        var slime = new ActorPixelLang(MapaPixelLang.Cargar().Personaje("Slime"));
        slime.Iniciar(0f);
        slime.Enviar("recibir_golpe", 0f);                    // Patrulla -> Aturdido, vida 20
        int t = slime.Enviar("fin_aturdimiento", 0f);         // vida > 0: vuelve a Persecucion
        Assert.AreEqual("Persecucion", slime.Estado);
        Assert.AreEqual("", slime.Delta[t].guarda);
        slime.Enviar("recibir_golpe", 0f);
        slime.Enviar("recibir_golpe", 0f);                    // Aturdido -> Aturdido, vida 0
        t = slime.Enviar("fin_aturdimiento", 0f);
        Assert.AreEqual("Aplastado", slime.Estado);
        Assert.AreEqual("vida <= 0", slime.Delta[t].guarda);
        Assert.IsTrue(slime.EnEstadoFinal);
        Assert.AreEqual(-1, slime.Enviar("ver_jugador", 0f), "un estado final no tiene transiciones");
    }

    [UnityTest]
    public IEnumerator LaEscenaMuestraLosMismosEstados()
    {
        SceneManager.LoadScene("DemoPixelLang");
        yield return null;
        yield return null;
        var demo = Object.FindAnyObjectByType<DemoPixelLang>();
        Assert.IsNotNull(demo, "La escena DemoPixelLang no tiene el componente DemoPixelLang");
        demo.pausa = 0f;
        demo.EjecutarSimulacion();
        float limite = Time.realtimeSinceStartup + 30f;
        while (!demo.Terminado && Time.realtimeSinceStartup < limite)
            yield return null;
        yield return null;   // Update dibuja el último estado
        Assert.IsTrue(demo.Terminado, "La simulación no terminó");
        Assert.AreEqual(demo.TotalPasos, demo.Coincidencias);
        var mapa = MapaPixelLang.Cargar();
        var pasos = mapa.simulaciones[0].pasos;
        Assert.AreEqual(pasos[pasos.Length - 1].estado, demo.EstadoMostrado);
    }

    [UnityTest]
    public IEnumerator LaPartidaDeDemostracionTerminaConLosSlimesAplastados()
    {
        SceneManager.LoadScene("JuegoPixelLang");
        yield return null;
        yield return null;
        var juego = Object.FindAnyObjectByType<JuegoPixelLang>();
        Assert.IsNotNull(juego, "La escena JuegoPixelLang no tiene el componente JuegoPixelLang");
        Assert.AreEqual(juego.Caballero.Datos.inicial, juego.Caballero.Estado);
        Assert.AreEqual(2, juego.Slimes.Length, "el minijuego tiene dos slimes");
        Assert.AreEqual(1, juego.Slimes[0].Instancia);
        Assert.AreEqual(3, juego.Slimes[1].Instancia);
        foreach (var slime in juego.Slimes)
            Assert.AreEqual(slime.Datos.inicial, slime.Estado);
        Time.timeScale = 3f;
        juego.IniciarDemostracion();
        float limite = Time.realtimeSinceStartup + 40f;
        while (!juego.FinDePartida && Time.realtimeSinceStartup < limite)
            yield return null;
        Time.timeScale = 1f;
        Assert.IsTrue(juego.FinDePartida, "La partida no terminó");
        foreach (var slime in juego.Slimes)
            Assert.AreEqual("Aplastado", slime.Estado);
        Assert.AreEqual("Reposo", juego.Caballero.Estado);
        Assert.AreEqual(75, (int)juego.Caballero.Valor("vida"), "el caballero recibió un solo golpe");
    }
}
