using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;

// Nivel 9 del plan de validación: la biblioteca que genera el compilador, usada desde Unity,
// da los mismos estados y atributos que la máquina de código de tres direcciones (la traza
// está en Resources/pixellang.json), y la escena muestra esos mismos estados.
// Se ejecutan con: unity test <proyecto> --mode PlayMode
public class PruebasPixelLang
{
    [Test]
    public void LaBibliotecaDaLaMismaTrazaQueElTAC()
    {
        var mapa = MapaPixelLang.Cargar();
        var simulacion = mapa.simulaciones[0];
        var personaje = new PersonajeNativo(mapa.personajes[simulacion.personaje]);
        for (int i = 0; i < simulacion.pasos.Length; i++)
        {
            var paso = simulacion.pasos[i];
            if (i == 0)
                personaje.Iniciar();
            else
                personaje.Enviar(paso.evento);
            Assert.IsTrue(personaje.Coincide(paso),
                $"Paso {i} ({paso.evento}): la máquina de TAC da {paso.estado} y la biblioteca, {personaje.Estado}");
        }
    }

    [Test]
    public void LaBibliotecaRechazaIndicesInvalidos()
    {
        Assert.AreEqual(3, PixelLangNative.pl_iniciar(-1));
        Assert.AreEqual(3, PixelLangNative.pl_evento(0, 999));
        Assert.AreEqual(-1, PixelLangNative.pl_estado(42));
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
}
