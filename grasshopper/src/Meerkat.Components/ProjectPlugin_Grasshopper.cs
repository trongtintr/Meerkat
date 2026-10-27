using System;
using System.IO;
using System.Text;
using System.Reflection;
using System.Resources;
using SD = System.Drawing;

using Rhino;
using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class AssemblyInfo : GH_AssemblyInfo
  {
    static readonly string s_assemblyIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAq1JREFUSEvlle9LU1EYx/cHREj4oheDKQsyt1z0w5ZWQ3pR7AhLowIjohlFu9ksNkaaNHzRDwuJIVgGGlFytiDNQRI4aAriXGOr3iXVQEiLppcgoldPPGe7l3vPqXapl33hy+7YOZ/vc855zp3J9F/J4bBUODZaquwbzC585n//JyHQVm0GtNNuwc8Pdqv5ID/ur+Txx7Y0n6NX7FbLDwwInaqFln1WFmarNo/w4w2LSDE/8dFVIkUBraxAa4etboGfV1Ye/1gVkWhWASt21G5Wwbua2mC/d7D0G83iHJ7zSzG4pmr08Z5JaO+dggOtHcUzcB3WBTP76KqhEKXylgtPoOtuDoanChCb+w5D8QXYZq9lAVttm+B0eFwMkWiW5+lEJNqpVHzn2TIDK247cV639/j91uP3rBAupJPnqsJl4gQejm6sdwoH3Df8AiLji8JW8VwmbEUccO3RWwZMzKfgXfYSfHvjYubhaEIOsa3z98/qQpDF801EioaxeoTPvpxQwejp0Z0CXFkBjscVc+cR5vksADslnsqD/JqAfL8GCsFKWLlqhuTIdgGuDUAbCggOpCGdGWXQz26T6pt71wlwPgCLKxuAg7KZe/ClfY0uoK9+rQBHP0h8UgO4bhID8GCOhuKQTCdgpWe9PqChQoCjFTjelbKHjCISlSNPF2Fp7hgLwZUUApXQ31EjwIm7VQ3oHsppAmie56rCS4KriM58hKVXJ9Uuut1VJwR4fd3FDppc5rbnDxcN5fZFc3iTH05/Ze068zwE3iM7GDQQvKje6N6BCQbHghQ4zuV5gkpvUrmp+QzsbihesD3ORvYZoRnwBW6w58uDKb5y2eMfM/YvhyFYDU5ECN5U3Gf02etJvmNY5YbhWhVfflTWwvSm+bJ7bkSl91RY69+2IqefdorUQK7KcYIAAAAASUVORK5CYII=";
    static readonly string s_categoryIconData = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAilJREFUOE9jYKAl0NLS4tFXl1fQl5cXQJcjCmgrymzUVpT5H+Ss/F1bSboAXR4r8ClaKuKds6rbO3vlfRNTx/8gAyx05P7rKCv809c2ckNXjwJ8slbZeGeveO6dvfI/CFu7JYENsHZL/u+ZvuA/SA6kBl0fGPhmrVTxzl7xOaRkw/+6OZf+T9/6/H9MSsV/HSXZ/97x7WADIXjFZ5BadP0M3tkrtiQ27v6/+ODH/6tOfP8/Z9v9/7oqCmAX2Fpa/+9ccee/b+4qmCEbUDQH5q6VCSxc93/Bvvf/95w+8//m+Zb/i6aEgjXDcHZp1//qmRfgLgHpQdieuzKkoP/E/2NnNv3/et72/5fT1v8n1+qhGNCz8AjYdTADfHJWBMAN8MpZntC08Nr/Vxtc/r8OZvn/yofxf4mtBIoBMzbeAHstrHQj2ACQHoQLcla4VM+68P9th9L/V14MYFxsKIRiwLLDH8AGBBSshbpitQPcgPj6/RxxdTu/X99d/f9NBt//N/Fc/0s8ZOGarc3MwZonrn8EsT17xWeQHrgBYFdkrehoW3j2/+3zdf+/XHb6X5Kk+d9YU/G/vprS/+DQhP/Ljnz+H1W1FWJ7zooWFM0gADLRO2PBidic7v9+fsFgW0ubZv9PTK/4n1Mz+39s7Q6o05cfwbAdBkKzVvF4Za9Y4Ze35n9S4+7/mR0HEbZCnL4CpAZdHwbwzF5mAvKSd/bKDWCctaIDJIauDgQA1/lTZFeDDFgAAAAASUVORK5CYII=";

    public static readonly SD.Bitmap PluginIcon = default;
    public static readonly SD.Bitmap PluginCategoryIcon = default;

    static AssemblyInfo()
    {
      if (!s_assemblyIconData.Contains("ASSEMBLY-ICON"))
      {
        using (var aicon = new MemoryStream(Convert.FromBase64String(s_assemblyIconData)))
          PluginIcon = new SD.Bitmap(aicon);
      }

      if (!s_categoryIconData.Contains("ASSEMBLY-CATEGORY-ICON"))
      {
        using (var cicon = new MemoryStream(Convert.FromBase64String(s_categoryIconData)))
          PluginCategoryIcon = new SD.Bitmap(cicon);
      }
    }

    public override Guid Id { get; } = new Guid("17a1a9cd-e5e2-42c7-9275-651037a73584");

    public override string AssemblyName { get; } = "Meerkat.Components";
    public override string AssemblyVersion { get; } = "0.1.3.20587";
    public override string AssemblyDescription { get; } = @"Meerkat – fast ENVI-met visualisation for Grasshopper: read EDX/EDT results, heatmaps, contours, wind and point probes.";
    public override string AuthorName { get; } = "Trong-Tin Tran";
    public override string AuthorContact { get; } = "trongtintr@outlook.com";
    public override GH_LibraryLicense AssemblyLicense { get; } = GH_LibraryLicense.unset;
    public override SD.Bitmap AssemblyIcon { get; } = PluginIcon;
  }

  public class ProjectComponentPlugin : GH_AssemblyPriority
  {
    static readonly Guid s_projectId = new Guid("17a1a9cd-e5e2-42c7-9275-651037a73584");
    static readonly dynamic s_projectServer = default;
    static readonly object s_project = default;

    static ProjectComponentPlugin()
    {
      s_projectServer = ProjectInterop.GetProjectServer();
      if (s_projectServer is null)
      {
        RhinoApp.WriteLine($"Error loading Grasshopper plugin. Missing Rhino3D platform");
        return;
      }

      // get project
      dynamic dctx = ProjectInterop.CreateInvokeContext();
      dctx.Inputs["projectAssembly"] = typeof(ProjectComponentPlugin).Assembly;
      dctx.Inputs["projectId"] = s_projectId;
      dctx.Inputs["projectData"] = GetProjectData();

      object project = default;
      if (s_projectServer.TryInvoke("plugins/v1/deserialize", dctx)
            && dctx.Outputs.TryGet("project", out project))
      {
        // server reports errors
        s_project = project;
      }
    }

    public override GH_LoadingInstruction PriorityLoad()
    {
      if (AssemblyInfo.PluginCategoryIcon is SD.Bitmap icon)
      {
        Grasshopper.Instances.ComponentServer.AddCategoryIcon("Meerkat", icon);
      }
      Grasshopper.Instances.ComponentServer.AddCategorySymbolName("Meerkat", "Meerkat"[0]);

      return GH_LoadingInstruction.Proceed;
    }

    public static bool TryCreateScript(GH_Component ghcomponent, string serialized, out object script)
    {
      script = default;

      if (s_projectServer is null) return false;

      dynamic dctx = ProjectInterop.CreateInvokeContext();
      dctx.Inputs["component"] = ghcomponent;
      dctx.Inputs["project"] = s_project;
      dctx.Inputs["scriptData"] = serialized;

      if (s_projectServer.TryInvoke("plugins/v1/gh/deserialize", dctx))
      {
        return dctx.Outputs.TryGet("script", out script);
      }

      return false;
    }

    public static void DisposeScript(GH_Component ghcomponent, object script)
    {
      if (script is null)
        return;

      dynamic dctx = ProjectInterop.CreateInvokeContext();
      dctx.Inputs["component"] = ghcomponent;
      dctx.Inputs["project"] = s_project;
      dctx.Inputs["script"] = script;

      if (!s_projectServer.TryInvoke("plugins/v1/gh/dispose", dctx))
        throw new Exception("Error disposing Grasshopper script component");
    }

    static string GetProjectData()
    {
      var rm = new ResourceManager("Plugin.Data", Assembly.GetExecutingAssembly());
      return rm.GetString("PROJECT-DATA");
    }
  }
}
