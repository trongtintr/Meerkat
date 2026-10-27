using System;
using SD = System.Drawing;
using SWF = System.Windows.Forms;

using Rhino.Geometry;

using Grasshopper.Kernel;

namespace RhinoCodePlatform.Rhino3D.Projects.Plugin.GH
{
  public sealed class ProjectComponent_8772c612 : ProjectComponent_Base
  {
    static readonly string s_scriptDataId = "8772c612-d0fe-456f-8c5a-63f33c580ac8";
    static readonly string s_scriptIconData = "iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAAABGdBTUEAALGPC/xhBQAAAAlwSFlzAAAOwgAADsIBFShKgAAAApJJREFUSEvlVEtrE1EY7U/wB7gQl04eJrFV506SmVaa5E6TmZhKU0RbHysffQia+sBKLC6KNi2uJEKkSBG1oriwPtC4MVlUBJEgSLTqIu6iYgizaD/5JjODJjOJcakHPrjc75x77nwnuR0d/w2cfmkdQ8RRLFzX9/8aTr+0wcbSFMPSMsOGVmpFy7iHvXr+H4MhIs+QUIZhKTAszdpZOqz3cI17ag85ROR/VzfBJiIO2Vj6TDv4WjOxegnksBRQg9p6jgGN/IFh6VcbS2fb+XxtjLOoVc8wu1TNwHq+zUJuyMnMQEf9fB2cGEexwxuubA9EqyQYqTp9tKLucWLcKqeWYIg4ZiN9RRS7hJ2rw6MJyOXT8O7VBEwkJOjqDq1iz0HEInLr9ZbAoBxeKYdiOnRaGblwG/aOXwRPdxT8ff0ghGXY2iNC8lQvLKYIjO/nFOR6vIFcy5DtXLhk5yJKYM9ZGJl+DFPzBZi7swKZhx/h5tIDSE4nYGbmIHxa7ocfyzx8f+KCb7c2QuHSepiMd4KbCyouNlgyzaBmECnZvWgw2WBw//lTY0Tlwi4Tgy3gQQNiYaADg7J7pTx+tjh8RknMPbI0yKa3wbEDRBtRMN92yJt9Mv4voHfgyNq51GXDYOFqFAZ3h9aw5/aJ+LtvL2SPIKshHzqeVDI37sHJqRR09sTAHx4AIRKDrh2yuoc95KhfIMitQ3bxUsnNSwqKX7x8A8XPX4x6/fY9pK7Mq4XrX3vIRQ1q8QzTDAwDQTY1aFaGgSBbG+jAoDyCrIZ8+MR55e5StuFAvbCHHG1EbYfMu3lpAcWxfUer6euLxsG4xj01ZOQ0u3Er6C+l0xepcHSwioXrdl/cltBe0zGs+tf038ZPemMOJN8fnnwAAAAASUVORK5CYII=";

    public override Guid ComponentGuid { get; } = new Guid("8772c612-d0fe-456f-8c5a-63f33c580ac8");

    public override GH_Exposure Exposure { get; } = GH_Exposure.primary;

    public override bool Obsolete { get; } = false;

    public ProjectComponent_8772c612() : base(GetResource(s_scriptDataId), s_scriptIconData,
        name: "EDX_Reader",
        nickname: "EDX_Reader",
        description: @"Reads an ENVI-met EDX/EDT output file and extracts one variable on a plan (z) or vertical section (x / y) as a grid mesh with one value per cell. Also returns the date, time, unit, min / max, a ready-made legend title and a mask of building / no-data cells.",
        category: "Meerkat",
        subCategory: "1 | Read"
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
