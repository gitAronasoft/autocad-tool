import os
from src.architectural_analyzer import ArchitecturalAnalyzer
from src.autocad_integration import AutoCADIntegration

def main():
    """
    Demo interface for the AI-powered AutoCAD plugin
    """
    print("=" * 60)
    print("AI-POWERED AUTOCAD ARCHITECTURAL ANALYZER")
    print("=" * 60)
    print()
    
    print("🏗️  Welcome to your AI-powered AutoCAD plugin!")
    print("This tool can analyze architectural drawings and automatically:")
    print("• Detect floor plans vs elevation drawings")
    print("• Trace interior and exterior walls")
    print("• Identify garage and buffered spaces")
    print("• Detect doors and windows")
    print("• Generate proper AutoCAD layer names")
    print("• Create AutoCAD-compatible drawing commands")
    print()
    
    # Initialize components
    print("🔧 Initializing AI analyzer...")
    analyzer = ArchitecturalAnalyzer()
    
    print("🔧 Initializing AutoCAD integration...")
    autocad = AutoCADIntegration()
    
    print("✅ System ready!")
    print()
    
    # Demo the AutoCAD integration
    print("📋 Creating sample AutoCAD output...")
    
    # Create a new DXF document
    autocad.create_new_dxf()
    
    # Create layers based on your requirements from the transcript
    print("Creating layers for different wall types:")
    
    # Basement layers
    autocad.create_layer("basement_interior_wall", color=1)  # Red
    autocad.create_layer("basement_exterior_wall", color=2)  # Yellow
    
    # Main floor layers  
    autocad.create_layer("main_floor_interior_wall", color=1)  # Red
    autocad.create_layer("main_floor_exterior_wall", color=2)  # Yellow
    autocad.create_layer("main_floor_garage_wall", color=3)    # Green (buffered space)
    
    # Door and window layers
    autocad.create_layer("front_door_main", color=4)      # Cyan
    autocad.create_layer("front_window_main", color=5)    # Blue
    autocad.create_layer("patio_door_main", color=6)      # Magenta
    
    print("✅ Layers created successfully!")
    
    # Draw sample architectural elements
    print("Drawing sample walls and elements...")
    
    # Sample basement exterior wall (house perimeter)
    basement_exterior = [(0, 0), (200, 0), (200, 150), (0, 150), (0, 0)]
    autocad.draw_polyline(basement_exterior, "basement_exterior_wall")
    
    # Sample basement interior wall (inside the house)
    basement_interior = [(20, 20), (180, 20), (180, 130), (20, 130), (20, 20)]
    autocad.draw_polyline(basement_interior, "basement_interior_wall")
    
    # Sample garage area (main floor with buffered wall)
    garage_wall = [(50, 0), (120, 0), (120, 60), (50, 60)]
    autocad.draw_polyline(garage_wall, "main_floor_garage_wall")
    
    # Sample doors
    autocad.draw_rectangle((90, 0), (110, 8), "front_door_main")      # Front door
    autocad.draw_rectangle((150, 80), (170, 88), "patio_door_main")   # Patio door
    
    # Sample windows
    autocad.draw_rectangle((30, 0), (45, 5), "front_window_main")     # Front window
    
    print("✅ Sample elements drawn!")
    
    # Save the output file
    output_file = "AI_analyzed_drawing.dxf"
    autocad.save_dxf(output_file)
    
    print(f"📁 AutoCAD file saved as: {output_file}")
    
    # List all created layers
    print("\n📊 Created layers:")
    layers = autocad.list_layers()
    for layer in layers:
        print(f"   • {layer['name']} (Color: {layer['color']})")
    
    print("\n" + "=" * 60)
    print("READY FOR AI ANALYSIS!")
    print("=" * 60)
    print()
    print("Your AI-powered AutoCAD plugin is ready to:")
    print("1. Analyze uploaded architectural drawings (PDF or DXF)")
    print("2. Automatically detect walls, doors, windows")
    print("3. Generate proper layer names and colors")
    print("4. Create AutoCAD-compatible output")
    print()
    print("To use with your drawings:")
    print("• Upload architectural drawings to the project")
    print("• The AI will analyze and detect building elements")
    print("• Proper AutoCAD layers and geometry will be created")
    print("• Review and import into your AutoCAD workflow")
    print()
    print("🚀 Plugin demonstration completed successfully!")

if __name__ == "__main__":
    main()