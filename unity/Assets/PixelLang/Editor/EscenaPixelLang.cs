using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

// Crea las escenas (el minijuego y la validación) y construye el reproductor de Windows. Se usa
// desde el menú PixelLang del editor o en modo batch con la herramienta de línea de comandos:
//   unity run <proyecto> -- -executeMethod EscenaPixelLang.Crear
//   unity run <proyecto> -- -executeMethod EscenaPixelLang.ConstruirWindows
public static class EscenaPixelLang
{
    const string EscenaJuego = "Assets/Scenes/JuegoPixelLang.unity";
    const string EscenaValidacion = "Assets/Scenes/DemoPixelLang.unity";
    const string Plantilla = "Assets/Scenes/SampleScene.unity";
    const string SalidaPorDefecto = "Build/PixelLangDemo.exe";

    [MenuItem("PixelLang/Crear las escenas")]
    public static void Crear()
    {
        if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            return;
        CrearEscena<DemoPixelLang>(EscenaValidacion, "PixelLang");
        CrearEscena<JuegoPixelLang>(EscenaJuego, "Juego");
        // El reproductor empieza en el minijuego; con Tab se pasa a la validación
        EditorBuildSettings.scenes = new[]
        {
            new EditorBuildSettingsScene(EscenaJuego, true),
            new EditorBuildSettingsScene(EscenaValidacion, true),
        };

        PlayerSettings.companyName = "Grupo 5 UPC";
        PlayerSettings.productName = "PixelLang Demo";
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.defaultScreenWidth = 1280;
        PlayerSettings.defaultScreenHeight = 720;
        PlayerSettings.resizableWindow = true;
        PlayerSettings.runInBackground = true;
        AssetDatabase.SaveAssets();
        Debug.Log("PixelLang: escenas creadas en " + EscenaJuego + " y " + EscenaValidacion);
    }

    // La escena de la plantilla Universal 2D ya trae la cámara y la luz global 2D
    static void CrearEscena<T>(string ruta, string nombre) where T : MonoBehaviour
    {
        var escena = File.Exists(Plantilla)
            ? EditorSceneManager.OpenScene(Plantilla, OpenSceneMode.Single)
            : EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
        foreach (var anterior in UnityEngine.Object.FindObjectsByType<T>(FindObjectsSortMode.None))
            UnityEngine.Object.DestroyImmediate(anterior.gameObject);
        new GameObject(nombre).AddComponent<T>();
        Directory.CreateDirectory(Path.GetDirectoryName(ruta));
        EditorSceneManager.SaveScene(escena, ruta);
    }

    [MenuItem("PixelLang/Construir para Windows")]
    public static void ConstruirWindows()
    {
        if (!File.Exists(EscenaJuego) || !File.Exists(EscenaValidacion))
            Crear();
        string salida = SalidaPorDefecto;
        string[] args = Environment.GetCommandLineArgs();
        int k = Array.IndexOf(args, "-buildOutput");
        if (k >= 0 && k + 1 < args.Length)
            salida = args[k + 1];
        var opciones = new BuildPlayerOptions
        {
            scenes = new[] { EscenaJuego, EscenaValidacion },
            locationPathName = salida,
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None,
        };
        BuildReport reporte = BuildPipeline.BuildPlayer(opciones);
        Debug.Log("PixelLang: construcción " + reporte.summary.result + " en " + salida);
        if (Application.isBatchMode && reporte.summary.result != BuildResult.Succeeded)
            EditorApplication.Exit(1);
    }
}
