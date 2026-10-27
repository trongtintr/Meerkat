using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_d8ef66b7 : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "d8ef66b7-9d0e-46ad-a404-01514da53f07";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAq9JREFUSEvdlf9LE2Ecx/0nFIogCDJqarFZw3OzmDc3n00dXsuma5WZYtsvM6kFkYOKKBBH3zA8op/CQeVwuNSoExeMvtj9UJgUdJSBI8rLhu0HhSc+555rHtusLKIOXtz7uYPP6z7Pw3NPXt5/cxVRKFBEIU6JikJRVTl6suyZYpyBgLJ+nopCY8V6G9ZUNUvo6tqSJocXlyEXLtbVYKbJmth3EGFARSFcY1/KAONAIslaWno/pqwvCaCwxR2UONE7IfQNx7EvEJEKjoeZqfkphAFUj76e7lrKKTiSUx/w44Ku3jFJ0HPe9p4U8R2zfDDW/oJAbXQlLe6gAHQEYm/6huMgEbTmpoW2Q+jj3FCRAEQubn8F0nNHdSKMvwyVxMi7BjudzCrI1AHg9Pbg0p3mxXdX12CRzcef2QLef1gjddbt3oaFS2uj8Bxw1uuzd5BN0N3/ApdWmBfbHZQsgDuRlFaYF5yMXpJVVtF4C4UeKuvnFAD+VmoGil3zFssCYDKwDp9q0Qjw5XXWXbhEV41VVPVTZf2lNaBdCYu7nwc6Lz+a6Ls7wxOmb6hHjzSWfQJJr3fr81m2gCeIbEGYZKa2IvHTUwTErxfysAad+7XStMCUPL6wPjVl+dyq1oAISJGIf+NrmA4i8rdohJu+zfjBmQ25BWqjK2H19POANxB7tmyKBujRuduFPCCGNkmZPbnjrb2+MqGnTfMgkym38Mr6K3YwO7mHlzfWS8v3nLbRxkMI2xpybLTVClbcyX9coKadotUT5IC9x8Ox1rP3OcKtkXB4ZHyQA0ajITkD96J3Bkg22V1iVkF6B6l/kjy+MjjNk25YWPi07tjhOEcy/OL/nkA6cEzNEmrjgSTJgIFxJ0yNHRiotHvkDBiYdpFktWF3ZgEcc/Did5DxyPxnr29lA4+Cv8mm2AAAAABJRU5ErkJggg==";

    public override Guid ComponentGuid { get; } = new Guid("d8ef66b7-9d0e-46ad-a404-01514da53f07");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_d8ef66b7() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "Heatmap",
        nickname: "Heatmap",
        description: @"Fast heatmap and contour map for ENVI-met data. Colours the reader mesh as flat cells, a smooth gradient or filled contour bands with isolines, value labels and hot-spot labels. It also builds the legend (ticks or value ranges) and the global title, both flat or upright in XZ. It is much faster than LB Spatial Heatmap.",
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
