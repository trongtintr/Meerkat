using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_3f4064b9 : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "3f4064b9-ef32-4fe3-8654-969e05c7d353";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAmVJREFUSEvVlMFrE0EUxgP+DRW8iC0ILQmlSmxrZpLsJtkkbmpNo9s2PRiiFxGagycD0oOFnPTQS5EoHlIPNinFJBa7jcVNLUYtbQxoI1aLGAUFoailkIM8mYUMmbWQbbzYD77Dvn3v9zFvYAyG/01dXqnFhHwDJixGjFafR5KkA9qepsVjd/gMclQuIGt1Ah+HILLvcEj4bLSJHdrePcuFXcEQsm1/woeh3m9xK5xD/M9/Cjlm83ecRvwXLbzmMm4FBxIqTa+r1+IdH0cnVFjFa4Lqu9dAtD2XpCHDiNsxoVOCdlaXPBbn7Cw2qqBvo0MqvKZaALmTTiyOamd1qRd7b0zhTnqC379+qPDqxhsaMIZ6trpQ34h2luqkZ7BotIhQs9kRAOFsmH5fRFYKIyHkJPX34EVO2ktYWr6B/PhQ+Ur9av09ZHNL9Dty+QrkcDsDrTnOd0MsdpP2EpaW3zBgcXkFLon9f8E38REY7h9iZpsKII5Gr8MtvpsJuOp2QXwq1TjA4Q/BvFKgTssKJFJZpjadkcHC9UEJt6nwGWwESRqBB7LC9BGWlm/oESRYKZWp84U1SGUXmNrc4jIsxdog4rKoAYNuO5Tv2kEprDJ9hKXl61pR/kURtu60wFjIDAMcD9PRdvh4j4Pi+kbjFe0loDJ5COavHYXv8YP6A8ixXpbK1EphDZKZHFMjKyIB9d5M2OBJYZXp23VFDv95kJXn1Bk5D4lklqklMwuQm5mAZ49uU6fvT0JazjN9hKXl614RcX3t4eOn+la0/wMaPXbEVjEIVl+QqQmBMJidAaa262O3b/UHHfmtnXozhCYAAAAASUVORK5CYII=";

    public override Guid ComponentGuid { get; } = new Guid("3f4064b9-ef32-4fe3-8654-969e05c7d353");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_3f4064b9() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "Point Probe",
        nickname: "Point Probe",
        description: @"Reads result values at any set of points from a result mesh (per face or per vertex, one or many variables). Returns values per point, ready-made text labels with units, the sampling location and distance, and an optional CSV table. Points on buildings can snap to the nearest valid cell.",
        category: "Meerkat",
        subCategory: "4 | Analyse"
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
