using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_9c83063a : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "9c83063a-abc4-40a6-b27d-51a2c6190e0d";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAwhJREFUSEvdlE9MknEcxjl56lDr0KG5ZugMhBdeeHkRBASNVxAQF6KGGG//cAa4iaUlmaYFKZu2XLZsqXlo/Vn/VmuuWlt1crXVVrpOND1Ulw7+qum6PA1mNbBTWK2e7Xt9Pnvfz2+PQPBfhdI5GyVaazibk+kc3szeVGi6akIt2rbIFtWCYbaD1jVCbvaBcuxGkdsPcWMztuwNQhoKQNu6F1y7D67Idvh6XAged+DQgAXRoTJ09RkX633msbRysdudI1fZ541rPdBv4qGh/FAZglA4WkF5OyAOdKGwsw/C/n5IR2LYOn4YDZdaEb7lR/+9Bkw8qcbUMw7PZ0rwNiGHZZt5PtmZBpGqK8lqAdjyCpJWnqTJGNvcagEsLm5uxRco5I4xVuRaYiVJBx4o9EkHfMqBJOlgxz5s8YcgDQWhDftR0cHDddgD/mgNQtEqdMYtiJ1MOVjy7jKfSyv/Flpnb5RorG3ZnExra8jsTcVgCdG0oW6G0jmJTO8k8lInoY1OojQ5CVNWTVTl1YTdunxlTqIyOYjKaCeMwUYYvY0odZVEqbESY7F11lvEyTL7BVSJe9ZsG4aXH0P4wCRODFzE+fGruH3nBqanbyORmMKnjw/wZeEuFmYv4t39ESQmongVbcfTgB+PqmsxpeIwuUkLo5KbyewXSDQOUmE7mzXg+kYWCjbjFf0RAFVSO8tVnsoacCGv+Oe/iDU1yRSG+jTJil+RrLbO8FKrNLM/ld86dvkyw4SwgF4U59Fg8otRWmiAVcyhhrJjB+1CM+NBm5pHxOBHd+U+9LpbEOXDiAfbMdjRiVO9RzAy2Ivjsc7Fuj17Vo5dodI0vz5nLQrX5EK7TgTHBhX43DLsF1YhJvJglGrCNaYN901deFx7DNOBOF70DOP16VG8uTKJtw8v48PLm/j8fgoVNZ6VYydiObJagKSntPIkrUBpnFstgKXOs3LshJR+bLOQXvrhoPS7A9+yg/3qnd8d9LlbENsZRjzUjqGDEQz3dePMUC+OxSJLnib/Xxi7fzZfASSuIDMuiruNAAAAAElFTkSuQmCC";

    public override Guid ComponentGuid { get; } = new Guid("9c83063a-abc4-40a6-b27d-51a2c6190e0d");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_9c83063a() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "Color palette",
        nickname: "Color palette",
        description: @"Provides ready-made colour gradients for Meerkat legends and maps, for example thermal comfort, wind speed or diverging palettes. You can also build a custom gradient from your own colours. The output list of colours connects directly to the _colors_ input of Heatmap or Streamline Color.",
        category: "Meerkat",
        subCategory: "2 | Visualise"
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
