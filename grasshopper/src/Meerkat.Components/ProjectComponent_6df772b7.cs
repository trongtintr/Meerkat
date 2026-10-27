using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_6df772b7 : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "6df772b7-1139-427a-ac87-055f8217f952";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAl5JREFUSEvllM9vElEQx/sn+A/4tujBRKzU1ougAr0YdtXdqIcajcWLh9LtD71ILxANaZv6A2NM3ce+fTTVBqqmvckNEo1y0ZroUdNDL3pqPSipF8x3ZRGeFtly9JtM8jJv5sO8nRm6uv57SZYRJ5bxnlj0hcTpuHjvSrcfzAdn53gIZ4nTXmIZnFh0k1i0Siz6HT4xx5WSc9kpjbJlwozVGhT2TuJ29VExvm1JnHfb1TJjw4Yy+pUwmnUqljjfJea4ErFoCeC9jH4Mm+bMiav5u0osX63ZihjvWngBqp1ILfBzE7m1BvgXdWy5s+ohJfYkJA/ni7/BuZIyvDQNvxjrSiJYG82tXkksdjaKjk6OLKUdcETPlQ/PzN8foGYxkjELYuyOpMTySTQQr/DwzDVnLDtepkbZ48mM4q/RNCoeZmw4i9aRMNfEoon6MjGa3XdjuufCzdmXY5NTz31BdeeTI3FTI4yuOVu6J5UaPOCXE77jp78F5MEKDGfbF1S7xfyWIoyma+BNz51bDw+FtMdev1w9E9UrdOFp9dP6Z9twhg93iPH55fb+g3YzIyndSxd6tYtvkTw0cv3HSqFUB4uGO8Qgtj+svfYGlO37sz+gDB08dmq9L6Ru6fFU9dWbD38AtzPEIge5YIDVBPceiSRRxYB6yRVYNOSCARaYTT/S45ejPrwgrG2NTrp/AXKQCwZYTfBG4Tv2h7Uyqojq8X/2ADG1HpRb9kAUJqMvpC4i+exlvZJ59KwOxhk+3CGm7Sn6mzDr+J6Y/aPy+QoMZ9vndg9aCdvrDSjjMDeb/BNy9BXixfIkKQAAAABJRU5ErkJggg==";

    public override Guid ComponentGuid { get; } = new Guid("6df772b7-1139-427a-ac87-055f8217f952");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_6df772b7() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "Wind_3D",
        nickname: "Wind_3D",
        description: @"Visualises the full 3D wind field from an ENVI-met atmosphere file as 3D arrows or traced streamlines. Streamlines can run in full 3D or on a plan / section slice and start from your own seed points or an automatic grid. Data is cached between runs for fast parameter changes.",
        category: "Meerkat",
        subCategory: "3 | Wind"
        )
    {
    }

    protected override void AppendAdditionalComponentMenuItems(SWF.ToolStripDropDown menu)
    {
      base.AppendAdditionalComponentMenuItems(menu);
      if (m_script is null) return;
      m_script.AppendAdditionalMenuItems(this, menu);
    }

    protected override void RegisterInputParams(GH_InputParamManager _) { }

    protected override void RegisterOutputParams(GH_OutputParamManager _) { }

    protected override void BeforeSolveInstance()
    {
      if (m_script is null) return;
      m_script.BeforeSolve(this);
    }

    protected override void SolveInstance(IGH_DataAccess DA)
    {
      if (m_script is null) return;
      m_script.Solve(this, DA);
    }

    protected override void AfterSolveInstance()
    {
      if (m_script is null) return;
      m_script.AfterSolve(this);
    }

    public override void RemovedFromDocument(GH_Document document)
    {
      ProjectComponentPlugin.DisposeScript(this, m_script);
      base.RemovedFromDocument(document);
    }

    public override BoundingBox ClippingBox
    {
      get
      {
        if (m_script is null) return BoundingBox.Empty;
        return m_script.GetClipBox(this);
      }
    }

    public override void DrawViewportWires(IGH_PreviewArgs args)
    {
      if (m_script is null) return;
      m_script.DrawWires(this, args);
    }

    public override void DrawViewportMeshes(IGH_PreviewArgs args)
    {
      if (m_script is null) return;
      m_script.DrawMeshes(this, args);
    }
  }
}
