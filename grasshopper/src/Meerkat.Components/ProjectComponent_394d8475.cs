using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_394d8475 : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "394d8475-2ff7-4414-b07b-58414250fe3e";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAAbdJREFUSEvdlT1Lw2AQx/tJFF8GsRQdpGqRgoODBeusk5POTk6Kq1MnhzY1fUlM60tbULAVSlGwg8WiBREU7NLFL+B88j/ylPA0STHtooE/JHeX+13vnkt9vn9zBUKRLX8oQsMQcsn5fXCcFm/os/M1kGLxLEPk/AyQg73KM6D+0e6x2dldAUrjiSbSSVq5PKdM85lthdYrHdzd01LeYN92pUytdoe1eX1FI2qC/Xh2BSARgsdTCq2Xit2KprMq2xfyOk2mk3T79t6tfMME7NVq/QEIAAQSwZC4F1Vb2yFA1mdHgPyiV/UFyBVZJdpjlRzvCkB7wmcG9xX9hS3bfOEhYqBjKYVm9QzHHT82KFoqUNDQaD6ns80VIAY2lTnhYaLfRw91tkHLF3kKaGnarVY5EXxrJmDO0PoDcCxRlfyzxYuy3cnmCJBf9CrPALlSJ58rAAsTNHQeqDjzODkYMvoP7ZtbixgMGbJusyMATgSOqgnaqZS7FYnh4/QEczrHiS3GkCHrNjsCkAwDFd8gWUhqt8nCJ+5dAcOQLWAmHP2OxbWe4N8KOWwB/sXVQ0DgHFS2f5l/9voBc53H+NiQIigAAAAASUVORK5CYII=";

    public override Guid ComponentGuid { get; } = new Guid("394d8475-2ff7-4414-b07b-58414250fe3e");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_394d8475() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "Wind_Vectors",
        nickname: "Wind_Vectors",
        description: @"Draws flat wind arrows from ENVI-met Flow u / v / w on a plan or vertical section. Arrow length scales with the in-plane wind speed against a fixed or automatic reference speed. Outputs an arrow mesh with speeds for colouring, plus points and 3D vectors.",
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
