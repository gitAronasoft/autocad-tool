# AI-Powered AutoCAD Wall Boundary Tracer - SaaS Application

## Overview
This project is a SaaS application designed to automate the tracing of wall boundaries from PDF architectural drawings. It processes floor plans to identify inner and outer wall lines, including garage spaces, and generates DXF files compatible with AutoCAD. The DXF output includes the original drawing content and newly traced boundaries on properly named, distinct layers, facilitating easy measurement extraction. The ultimate vision is to create a tool capable of full automation, including measurement extraction and integration with other estimation tools, minimizing human intervention.

## User Preferences
- Communication: Simple, everyday language
- Focus: Production-ready, accurate wall tracing
- Priority: Speed (< 30s) + proper AutoCAD layer naming

## System Architecture

### Core Processing Strategy
The system primarily uses a vector-based geometric approach for wall detection due to limitations with AI vision for precise tracing. AI is leveraged only for metadata analysis.

**Processing Flow (Vector-Based Approach)**:
1.  **PDF Upload**: User uploads a PDF.
2.  **PDFProcessor Service**: Extracts all vector paths from the PDF and converts the page to a 300 DPI image for metadata analysis.
3.  **VectorWallDetector Service**: Filters wall segments by stroke color (black) and line weight (≥0.2pt), groups connected segments into accurate wall boundaries, and classifies them as exterior outer, exterior inner, or interior walls. This service processes all path commands (m, l, c, qu, re, h) to preserve curves and geometric detail. It uses a KDTree for vertex snapping and graph-based loop tracing for precision.
4.  **FloorPlanAnalyzer Service (AI for Metadata Only)**: Utilizes AI (GPT-4o Vision) to detect the floor type (basement/main/second/terrace) with 95% confidence and identify the presence of a garage. It does *not* perform wall tracing.
5.  **DXFBuilder Service**: Combines the original PDF vectors onto an `ORIGINAL_DRAWING` layer with the vector-based wall boundaries onto properly named layers (e.g., `[floor_type]_exterior_outer`, `[floor_type]_exterior_inner`, `[floor_type]_interior_walls`, `[floor_type]_garage_wall`).
6.  **DXF Download**: The user downloads the generated DXF file, ready for AutoCAD.

### Key Design Decisions
*   **Vector-Based Wall Detection**: Prioritizes processing actual PDF geometry over AI vision inference for accuracy.
*   **AI for Metadata Only**: GPT-4o Vision is used solely for high-level classifications like floor type and garage presence.
*   **Preservation of Original Drawing**: The DXF output includes all original PDF vectors, ensuring completeness.
*   **Geometric Filtering & Classification**: Walls are identified by stroke color, line weight, and grouped into coherent boundaries, then classified based on their spatial relationship. A combined metric of `perimeter × √(num_points)` is used to accurately identify main wall boundaries, preventing small features from being misidentified.
*   **Standardized Layer Organization**: Layers in the DXF output follow a strict naming convention and color scheme (e.g., Yellow for exterior outer, Magenta for exterior inner) for AutoCAD compatibility.
*   **Robustness**: Handles various PDF drawing styles and complex geometries, processing curves and polylines accurately.

### Technology Stack
*   **Backend**: Flask (Python 3.11)
*   **Wall Detection**: Custom VectorWallDetector (geometric/CV approach)
*   **AI Metadata**: OpenAI GPT-4o Vision
*   **PDF Processing**: PyMuPDF (fitz)
*   **DXF Generation**: ezdxf (AutoCAD R2010 format)
*   **Geometry Processing**: NumPy
*   **Storage**: Local filesystem

## External Dependencies
*   **OpenAI API**: For GPT-4o Vision, used by the `FloorPlanAnalyzer` for floor type and garage detection.
*   **PyMuPDF (fitz)**: Python library for PDF processing, used by `PDFProcessor` for vector extraction and image conversion.
*   **ezdxf**: Python library for creating and modifying DXF files, used by `DXFBuilder` to generate AutoCAD-compatible outputs.
*   **NumPy**: Python library for numerical operations, utilized for geometric calculations in wall detection.