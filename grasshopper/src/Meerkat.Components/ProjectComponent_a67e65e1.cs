using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_a67e65e1 : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "a67e65e1-5088-4798-ab93-16f575aaacd5";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAl5JREFUSEvVkl1oUnEYxnfbx4U3sTDU6DKsWVuxyHE8taNz2hTMRq19KN05GLOLuglddJEx0G6CiOUWrIJKIaGpjY5tkNG2zsnWbvowyT85Ko5uu3/jXXTQwxwTz0U98IMHn/P6cDhPQ8O/KiGo1El/k0XANimKk2r212gjFDxKIW/TiEX7KedO7TGr60DbqYGDDLOj4vC0N+JzjyTZ4dArzj+WYUORL0NRNqsofwY4m6KU1HHF+2r4OdpYXB5UwjeLSshTf0q6KCY+xugAsRlOTImHFs9DzuGNgnvkOQyH0uC/+x5CT7IwkfgkxGdj4cybAFX4MGBbXaC5laQOhEk1LwQ1isLgnvG8VQU5vZrF/zFQDPl+QQkI+vKClMMb5d1Xp+0Xg2mDL5yxBx9nUxPJz5CYjcG7uQAsL/bD2lsaSskmXohq1t9MGNIo8lYVn9Or+fUCmiE/fLsBQS8WVNMDNrs3PvN0nJ+7nios9vOrC7Qfv4H0ub+iGYYIt3cBgl6a16SNVkSbjKT0aB8g6KX5lrTZimhzB1mZPgQI+opDOVZEd5rJ2rwBEPTioVwroi0WIiw5AUFfXiDLiiiLnXzkLgOCXiyoplpX1NbpIOnXdwBBL81r0kYrOm7uJrGXLwBBL823pM1W1NrRQ8KJHCDoKw7lWNFRUw+5GfkKCHrxUK4VHTGeI9fuLQGCvrxAlhW1MGfJpVvzgKAXC6qp1hUdPtlNPDdmAEEvzeuWjj5D+q7EAUEvzetWi6l3qr0vAO3nA9Bs7H0mzetWs9W6Xavvcmn1Vldrq3ObNP8/9Ru8sFBvi4yrjgAAAABJRU5ErkJggg==";

    public override Guid ComponentGuid { get; } = new Guid("a67e65e1-5088-4798-ab93-16f575aaacd5");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_a67e65e1() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "Streamline colors",
        nickname: "Streamline colors",
        description: @"Colours streamline curves by local ENVI-met wind speed. Builds smooth vertex-coloured tubes, coloured segments for custom previews and a speed legend (flat or upright in XZ). Shares the data cache with Wind 3D, so the file is read only once.",
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
