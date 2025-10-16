# AI-Powered AutoCAD Wall Boundary Tracer - SaaS Application

## Overview
A SaaS-ready tool that processes PDF architectural drawings and automatically traces wall boundaries, creating DXF files with properly named layers for AutoCAD. The system preserves the original drawing and adds AI-traced boundary highlights for easy measurement extraction.

## Product Vision & Roadmap

### Stage 1: Floor Plans (CURRENT PRIORITY - MVP)
**Objective**: Automatically trace wall boundaries in floor plan drawings

**What It Does**:
- Upload PDF architectural drawing (basement, main floor, second floor, etc.)
- AI detects floor type automatically (basement/main/second/garage)
- Traces **inner boundary** (interior wall line) 
- Traces **outer boundary** (exterior wall line)
- Detects **garage spaces** and traces garage wall (buffered/protected space)
- Generates DXF with original drawing + boundary highlights

**Layer Naming Convention**:
- `[floor_type]_exterior_outer` - Outer edge of exterior walls (building perimeter)
- `[floor_type]_exterior_inner` - Inner edge of exterior walls (conditioned space boundary)
- `[floor_type]_interior_walls` - Interior wall boundaries (room dividers)
- `[floor_type]_garage_wall` - Wall separating garage from conditioned space

**Examples**:
- `basement_exterior_outer`, `basement_exterior_inner`, `basement_interior_walls`
- `main_floor_exterior_outer`, `main_floor_exterior_inner`, `main_floor_interior_walls`, `main_floor_garage_wall`
- `second_floor_exterior_outer`, `second_floor_exterior_inner`, `second_floor_interior_walls`

**Output**: DXF file ready for AutoCAD containing:
- ORIGINAL_DRAWING layer - Complete PDF vector content (walls, dimensions, text, etc.)
- Traced boundary layers with proper names
- Ready for measurement extraction in AutoCAD

**Success Criteria**:
- AI correctly identifies floor type
- Boundary traces are accurate
- DXF opens in AutoCAD with all layers properly named
- Processing time < 30 seconds per drawing

### Stage 2: Elevations (FUTURE)
**Objective**: Detect and trace doors/windows in elevation views

**Features**:
- Detect elevation type (front/back/left/right view)
- Trace door shapes: `front_door_main`, `back_door_basement`
- Trace window shapes: `front_window_main`, `left_window_basement`
- Trace door windows: `front_door_window`
- Layer naming: `[direction]_[element]_[floor]`

**Output**: DXF with elevation elements traced on named layers

### Stage 3: Advanced Automation (FUTURE)
**Objective**: Full automation with measurements and batch processing

**Features**:
- Height calculations from elevation data
- Automatic measurement extraction (area, perimeter, XYZ)
- Excel export of all measurements
- Batch processing of multiple drawings
- Quality validation and error detection
- Integration with HVAC/estimation tools

**Vision**: Zero human intervention - upload → process → export measurements

## Architecture

### Core Processing Strategy

**Key Discovery (Oct 16, 2025)**: GPT-4o Vision has a fundamental limitation with precise geometric tracing - it consistently returns simple rectangles (4-5 points) instead of following actual wall lines, regardless of prompt engineering.

**Solution**: Process PDF vector geometry directly instead of AI vision inference.

**Processing Flow (Vector-Based Approach)**:
```
1. PDF Upload
   ↓
2. PDFProcessor Service
   - Extract all vector paths from PDF (~13,000+ paths)
   - Convert page to 300 DPI image for metadata analysis
   ↓
3. VectorWallDetector Service (NEW - Geometric Approach)
   - Filter wall segments by stroke color (black) and line weight (≥0.2pt)
   - Group connected segments into wall boundaries
   - Classify as exterior outer, exterior inner, or interior walls
   - Output: Accurate polylines following actual drawn wall geometry
   ↓
4. FloorPlanAnalyzer Service (AI for Metadata Only)
   - Detect floor type (basement/main/second/terrace) - 95% confidence
   - Detect garage presence
   - No wall tracing (AI limitation identified)
   ↓
5. DXFBuilder Service
   - Add original PDF vectors to ORIGINAL_DRAWING layer
   - Add vector-based wall boundaries to proper layers
   - Create layers with naming: [floor_type]_[exterior_outer|exterior_inner|interior_walls]
   - Output complete DXF file
   ↓
6. Download DXF → Open in AutoCAD
```

### Service Architecture

```
┌─────────────────────────────────────────┐
│         Flask Web Application           │
│     (Upload, Progress, Download)         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        Processing Pipeline              │
│                                         │
│  PDFProcessor                           │
│  ├─ Extract ~13,000 vector paths        │
│  └─ Generate 300 DPI image for AI       │
│                                         │
│  VectorWallDetector (NEW)               │
│  ├─ Filter wall segments (black, ≥0.2pt)│
│  ├─ Group connected segments            │
│  ├─ Classify exterior vs interior       │
│  └─ Output accurate wall polylines      │
│                                         │
│  FloorPlanAnalyzer (AI - Metadata Only) │
│  ├─ Floor type detection (95% accuracy) │
│  └─ Garage presence detection           │
│                                         │
│  DXFBuilder                             │
│  ├─ ORIGINAL_DRAWING layer (PDF vectors)│
│  ├─ Vector-based wall boundary layers   │
│  └─ Layer naming: [floor]_[wall_type]  │
└─────────────────────────────────────────┘
```

### Key Design Decisions

1. **Vector-Based Wall Detection**: Process actual PDF geometry instead of AI vision inference
2. **AI for Metadata Only**: GPT-4o used only for floor type and garage detection (not wall tracing)
3. **Preserve Original Drawing**: Extract and include all PDF vectors in DXF (99.9%+ accuracy)
4. **Geometric Filtering**: Identify walls by stroke color (black) and line weight (≥0.2pt)
5. **Segment Grouping**: Connect nearby line segments into coherent wall boundaries
6. **Layer Organization**: `[floor]_exterior_outer`, `[floor]_exterior_inner`, `[floor]_interior_walls`
7. **Production-Ready**: Error handling, logging, scalability

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **Wall Detection**: VectorWallDetector (geometric/CV approach)
- **AI Metadata**: OpenAI GPT-4o Vision (floor type, garage detection only)
- **PDF Processing**: PyMuPDF (fitz) - vector extraction + image conversion
- **DXF Generation**: ezdxf - AutoCAD R2010 format
- **Geometry Processing**: NumPy - spatial calculations
- **Storage**: Local filesystem (ready for cloud migration)

### Layer Structure in Output DXF

```
ORIGINAL_DRAWING (color: white)
├─ All PDF vector paths (walls, dimensions, text, symbols)
├─ Preserves complete architectural drawing
└─ ~13,000+ entities for typical drawing

[floor_type]_exterior_outer (color: yellow)
├─ Outer edge of exterior walls
└─ Building perimeter (outermost wall line)

[floor_type]_exterior_inner (color: magenta)
├─ Inner edge of exterior walls
└─ Conditioned space boundary

[floor_type]_interior_walls (color: cyan)
├─ Interior wall boundaries
└─ Room divider walls

[floor_type]_garage_wall (color: green)
├─ Garage separation wall
└─ Wall between conditioned space and garage
```

## User Preferences
- Communication: Simple, everyday language
- Focus: Production-ready, accurate wall tracing
- Priority: Speed (< 30s) + proper AutoCAD layer naming

## Environment Configuration
- **SESSION_SECRET**: Flask session management
- **OPENAI_API_KEY**: AI analysis (Replit integration)
- **Port**: 5000 (Flask development server)

## Development Status
- **Current Phase**: Rebuilding with optimal PDF vector + AI trace approach
- **Next Milestone**: Stage 1 MVP - Floor plan boundary tracing
- **Future Expansion**: Stage 2 (Elevations) → Stage 3 (Full automation)

## Recent Architecture Evolution

### October 16, 2025 - Vector-Based Wall Detection Implementation

**Critical Discovery**: GPT-4o Vision has a fundamental limitation with precise geometric tracing - it consistently returns simple rectangles (4-5 points) instead of following actual wall lines, regardless of prompt engineering.

**Root Cause Analysis**:
- AI vision inference cannot reliably trace dense geometric boundaries
- Multiple prompt variations all resulted in 4-5 point rectangles
- AI suitable only for high-level metadata (floor type, garage detection)

**Solution - Vector-Based Approach**:
1. **PDFProcessor** extracts ~13,000 vector paths from PDF (actual wall geometry)
2. **VectorWallDetector** (NEW) processes paths directly:
   - Filters walls by stroke color (black) and line weight (≥0.2pt)
   - Groups connected line segments into boundaries
   - Classifies as exterior outer, exterior inner, or interior walls
3. **FloorPlanAnalyzer** (AI) only for metadata:
   - Floor type detection: 95% confidence
   - Garage presence detection
   - No wall tracing
4. **DXFBuilder** outputs layered DXF with proper naming

**Results Comparison**:
| Boundary Type | AI Vision | Vector-Based | Improvement |
|--------------|-----------|--------------|-------------|
| Exterior Outer | 5 points (rectangle) | 16 points | 3.2x more detail |
| Exterior Inner | 5 points (rectangle) | 32 points | 6.4x more detail |
| Interior Walls | 3 rectangles | 332 segments | Actual geometry |

**Current Status**:
- ✓ Exterior walls: Accurate (16-32 points following actual drawn lines)
- ⚠️ Interior walls: Fragmented (332 segments need merging for production quality)
- ✓ AI metadata: Floor type 95% confidence, garage detection working
- ✓ Original drawing preserved: 13,089/13,099 paths (99.9%+)

**Future Refinements Needed**:
- Implement spatial index (KD-tree) for better segment merging
- Add colinear segment detection and merging
- Filter out tiny artifacts (< physical threshold)
- Expected result: 20-30 coherent interior walls vs current 332 fragments

**Architect Review**: Vector-based approach is sound, segment grouping algorithm needs refinement for production quality. Current implementation functional for testing.
