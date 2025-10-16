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
- `[floor_type]_interior` - Inner wall boundary
- `[floor_type]_exterior` - Outer wall boundary  
- `[floor_type]_garage_wall` - Wall adjacent to garage (buffered space)

**Examples**:
- `basement_interior`, `basement_exterior`
- `main_floor_interior`, `main_floor_exterior`, `main_floor_garage_wall`
- `second_floor_interior`, `second_floor_exterior`

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

**Key Insight**: PDF already contains complete vector drawing (13,000+ paths). AI's job is to **analyze and trace boundaries**, not reconstruct the drawing.

**Processing Flow**:
```
1. PDF Upload
   ↓
2. PDFProcessor Service
   - Extract all vector paths from PDF (preserve original drawing)
   - Convert page to 300 DPI image for AI analysis
   ↓
3. FloorPlanAnalyzer Service (Single AI Call)
   - Analyze image to detect floor type
   - Trace outer boundary (exterior wall) → coordinates
   - Trace inner boundaries (interior walls) → coordinates
   - Detect garage and trace garage wall → coordinates
   ↓
4. DXFBuilder Service
   - Add original PDF vectors to ORIGINAL_DRAWING layer
   - Convert AI coordinates to DXF polylines
   - Create boundary layers with proper names
   - Output complete DXF file
   ↓
5. Download DXF → Open in AutoCAD
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
│  ├─ Extract vector paths                │
│  └─ Generate AI-ready image             │
│                                         │
│  FloorPlanAnalyzer                      │
│  ├─ Single optimized AI call            │
│  ├─ Floor type detection                │
│  └─ Boundary coordinate extraction      │
│                                         │
│  DXFBuilder                             │
│  ├─ Original drawing layer              │
│  ├─ Boundary trace layers               │
│  └─ Proper layer naming                 │
└─────────────────────────────────────────┘
```

### Key Design Decisions

1. **Preserve Original Drawing**: Extract and include all PDF vectors in DXF
2. **Single AI Call**: One comprehensive request per page (fast + cost-effective)
3. **Structured Output**: AI returns JSON with floor type + boundary coordinates
4. **Layer Validation**: Ensure names follow `[floor]_[type]` convention
5. **Production-Ready**: Error handling, logging, caching for scalability

### Technology Stack
- **Backend**: Flask (Python 3.11)
- **AI**: OpenAI GPT-4o Vision (single optimized call)
- **PDF Processing**: PyMuPDF (fitz) - vector extraction + image conversion
- **DXF Generation**: ezdxf - AutoCAD R2010 format
- **Image Processing**: Pillow - AI image preparation
- **Storage**: Local filesystem (ready for cloud migration)

### Layer Structure in Output DXF

```
ORIGINAL_DRAWING (color: white)
├─ All PDF vector paths (walls, dimensions, text, symbols)
├─ Preserves complete architectural drawing
└─ ~13,000+ entities for typical drawing

[floor_type]_exterior (color: yellow)
├─ Outer boundary polyline
└─ Building perimeter trace

[floor_type]_interior (color: cyan)  
├─ Inner boundary polylines
└─ Room/space boundary traces

[floor_type]_garage_wall (color: green)
├─ Garage-adjacent wall trace
└─ Buffered space boundary
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

### October 16, 2025 - Production-Ready Architecture Complete
**Discovery**: PDF contains 13,000+ vector paths (complete drawing already exists)

**Implemented Solution**:
- Extract original PDF vectors → preserve in DXF (99.9%+ accuracy)
- AI analyzes image → traces boundaries only (single optimized call)
- Combine: Original drawing + AI boundary layers
- Result: Complete DXF with proper layer organization

**Key Achievements**:
- Vector preservation: 13,089/13,099 (99.9%+) ✓
- Single AI call per page (reduced from 3-5 calls) ✓
- Processing time: ~30 seconds per drawing ✓
- Proper layer naming: `[floor_type]_[boundary_type]` ✓
- Production-ready services: PDFProcessor, FloorPlanAnalyzer, DXFBuilder ✓

**Technical Fix (Critical)**:
- Fixed DXFBuilder to handle all PyMuPDF path formats correctly
- Now processes: move ('m'), line ('l'), curve ('c'), quad bezier ('qu'), rectangle ('re')
- Previously only captured 4% of vectors, now 99.9%+

**Architect Approved**: System ready for Stage 1 (floor plan) SaaS launch
