using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

// Crea la escena de demostración y construye el reproductor de Windows. Se usa desde el menú
// PixelLang del editor o en modo batch con la herramienta de línea de comandos de Unity:
//   unity run <proyecto> -- -executeMethod EscenaPixelLang.Crear
//   unity run <proyecto> -- -executeMethod EscenaPixelLang.ConstruirWindows
public static class EscenaPixelLang
{
    const string Escena = "Assets/Scenes/DemoPixelLang.unity";
    const string Plantilla = "Assets/Scenes/SampleScene.unity";
    const string SalidaPorDefecto = "Build/PixelLangDemo.exe";

    [MenuItem("PixelLang/Crear escena de demostración")]
    public static void Crear()
    {
        if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            return;
        // La escena de la plantilla Universal 2D ya trae la cámara y la luz global 2D
        var escena = File.Exists(Plantilla)
            ? EditorSceneManager.OpenScene(Plantilla, OpenSceneMode.Single)
            : EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
        foreach (var anterior in UnityEngine.Object.FindObjectsByType<DemoPixelLang>(FindObjectsSortMode.None))
            UnityEngine.Object.DestroyImmediate(anterior.gameObject);
        new GameObject("PixelLang").AddComponent<DemoPixelLang>();
        Directory.CreateDirectory(Path.GetDirectoryName(Escena));
        EditorSceneManager.SaveScene(escena, Escena);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(Escena, true) };

        PlayerSettings.companyName = "Grupo 5 UPC";
        PlayerSettings.productName = "PixelLang Demo";
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.defaultScreenWidth = 1280;
        PlayerSettings.defaultScreenHeight = 720;
        PlayerSettings.resizableWindow = true;
        PlayerSettings.runInBackground = true;
        AssetDatabase.SaveAssets();
        Debug.Log("PixelLang: escena creada en " + Escena);
    }

    [MenuItem("PixelLang/Construir para Windows")]
    public static void ConstruirWindows()
    {
        if (!File.Exists(Escena))
            Crear();
        string salida = SalidaPorDefecto;
        string[] args = Environment.GetCommandLineArgs();
        int k = Array.IndexOf(args, "-buildOutput");
        if (k >= 0 && k + 1 < args.Length)
            salida = args[k + 1];
        var opciones = new BuildPlayerOptions
        {
            scenes = new[] { Escena },
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
