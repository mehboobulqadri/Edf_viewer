"""
EDF Viewer Configuration Module
Contains all configuration constants, themes, and performance settings.
"""

import psutil
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Optional performance dependencies detection
try:
    import numba
    from numba import njit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

try:
    import cupy as cp
    try:
        cp.cuda.runtime.getDeviceCount()
        CUPY_AVAILABLE = True
        logging.info("CuPy GPU acceleration available")
    except (cp.cuda.runtime.CUDARuntimeError, Exception) as e:
        CUPY_AVAILABLE = False
        logging.warning(f"CuPy GPU test failed: {e}")
except ImportError:
    CUPY_AVAILABLE = False
    logging.info("CuPy not installed - GPU acceleration disabled")

try:
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor
    MULTIPROCESSING_AVAILABLE = True
except ImportError:
    MULTIPROCESSING_AVAILABLE = False

try:
    import h5py
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False

try:
    import numexpr as ne
    NUMEXPR_AVAILABLE = True
    ne.set_num_threads(psutil.cpu_count())
except ImportError:
    NUMEXPR_AVAILABLE = False

try:
    import lz4
    import blosc
    COMPRESSION_AVAILABLE = True
except ImportError:
    COMPRESSION_AVAILABLE = False

try:
    import sqlite3
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

try:
    import cProfile
    import pstats
    import tracemalloc
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False

# EXTREME PERFORMANCE CONFIGURATION
PERF_CONFIG = {
    # Ultra-high performance rendering
    'max_points_per_curve': 50000,  # Increased for ultimate quality
    'downsample_threshold': 500000,  # Much higher threshold for GPU acceleration
    'cache_size_mb': 2048,  # Massive cache for large datasets
    'render_threads': min(16, psutil.cpu_count()),  # Maximum threads
    'chunk_size': 5000000,  # Very large chunks for parallel processing
    'prefetch_chunks': 10,  # Extremely aggressive prefetching
    'target_fps': 240,  # Ultra-high target FPS
    'viewport_culling': True,
    'item_pooling': True,
    'async_rendering': True,
    'use_worker_threads': True,
    'render_ahead_frames': 3,  # Pre-render frames
    
    # Maximum GPU acceleration
    'use_gpu': CUPY_AVAILABLE,
    'gpu_memory_limit': 4096,  # 4GB GPU memory
    'gpu_batch_size': 128,  # Large batch processing for GPU
    'gpu_precision': 'float32',  # Optimized precision
    'gpu_stream_count': 4,  # Multiple GPU streams
    'gpu_concurrent_kernels': True,
    
    # Ultimate processing optimization
    'use_jit': NUMBA_AVAILABLE,
    'simd_width': 16,  # Maximum SIMD vector width (AVX-512)
    'parallel_processing': MULTIPROCESSING_AVAILABLE,
    'process_pool_size': min(8, psutil.cpu_count()),
    'use_shared_memory': True,
    'prefault_memory': True,  # Pre-fault memory pages
    'use_huge_pages': True,  # Use huge memory pages if available
    
    # Advanced memory optimization
    'memory_mapping': HDF5_AVAILABLE,
    'compression_level': 1,  # Fastest compression
    'memory_pool_size': 1024,  # 1GB memory pool
    'gc_threshold': 0.9,  # Higher memory threshold
    'use_compression': COMPRESSION_AVAILABLE,
    'use_database': DATABASE_AVAILABLE,
    'use_simd': NUMEXPR_AVAILABLE,
    'mmap_threshold': 50 * 1024 * 1024,  # 50MB threshold (lower for more mmap usage)
    'memory_alignment': 64,  # 64-byte memory alignment for SIMD
    'use_memory_pools': True,
    
    # Predictive and adaptive optimization
    'predictive_caching': True,
    'cache_prediction_window': 60.0,  # Longer prediction window
    'adaptive_quality': True,
    'quality_steps': 10,  # More quality steps
    'min_quality': 0.1,  # Lower minimum quality for extreme performance
    'adaptive_downsampling': True,
    'dynamic_optimization': True,
    'performance_feedback': True,
    
    # CPU optimization
    'cpu_affinity': True,  # Set CPU affinity for performance cores
    'disable_cpu_throttling': True,
    'use_performance_cores': True,
    'thread_priority_boost': True,
    
    # I/O optimization
    'use_direct_io': True,  # Bypass OS caching for large files
    'io_buffer_size': 1024 * 1024,  # 1MB I/O buffer
    'async_io': True,
    'readahead_size': 4 * 1024 * 1024,  # 4MB readahead
    
    # Developer and monitoring options
    'enable_profiling': PROFILING_AVAILABLE,
    'detailed_metrics': True,
    'performance_logging': True,
    'memory_tracking': True,
    'render_timing': True,
    'cache_statistics': True,
    'thread_monitoring': True,
    'gpu_monitoring': CUPY_AVAILABLE,
    'system_monitoring': True,
    'benchmark_mode': False,  # Can be enabled for testing
    'trace_memory_allocations': False,  # Very detailed but slow
    'profile_function_calls': False,  # Extremely detailed profiling
}

# Theme definitions
THEMES = {
    'dark': {
        'name': 'Dark Mode',
        'colors': {
            'primary_bg': '#181c20',
            'secondary_bg': '#2a2e36',
            'accent_bg': '#3c4043',
            'primary_text': '#e0e6ed',
            'secondary_text': '#b0b6bd',
            'accent_color': '#64b5f6',
            'success_color': '#4caf50',
            'warning_color': '#ff9800',
            'error_color': '#f44336',
            'grid_color': '#404040',
            'separator_color': '#555555',
            'highlight_color': '#1976d2',
            'selection_color': '#3f51b5'
        },
        'fonts': {
            'primary': ('Segoe UI', 10),
            'heading': ('Segoe UI', 12, 'bold'),
            'monospace': ('Consolas', 9)
        }
    },
    'light': {
        'name': 'Light Mode',
        'colors': {
            'primary_bg': '#ffffff',
            'secondary_bg': '#f5f5f5',
            'accent_bg': '#e0e0e0',
            'primary_text': '#212121',
            'secondary_text': '#757575',
            'accent_color': '#1976d2',
            'success_color': '#388e3c',
            'warning_color': '#f57c00',
            'error_color': '#d32f2f',
            'grid_color': '#e0e0e0',
            'separator_color': '#bdbdbd',
            'highlight_color': '#2196f3',
            'selection_color': '#3f51b5'
        },
        'fonts': {
            'primary': ('Segoe UI', 10),
            'heading': ('Segoe UI', 12, 'bold'),
            'monospace': ('Consolas', 9)
        }
    },
    'clinical': {
        'name': 'Clinical',
        'colors': {
            'primary_bg': '#fafafa',
            'secondary_bg': '#f0f0f0',
            'accent_bg': '#e8e8e8',
            'primary_text': '#1a1a1a',
            'secondary_text': '#666666',
            'accent_color': '#0066cc',
            'success_color': '#009688',
            'warning_color': '#ff6f00',
            'error_color': '#c62828',
            'grid_color': '#d0d0d0',
            'separator_color': '#bdbdbd',
            'highlight_color': '#1565c0',
            'selection_color': '#283593'
        },
        'fonts': {
            'primary': ('Segoe UI', 10),
            'heading': ('Segoe UI', 12, 'bold'),
            'monospace': ('Courier New', 9)
        }
    }
}

@dataclass
class Annotation:
    """Annotation data structure"""
    start_time: float
    duration: float
    description: str
    color: str
    timestamp: str
    channel: Optional[str] = None
    notes: str = ""

@dataclass
class SessionState:
    """Session state data structure"""
    file_path: str
    view_start_time: float
    view_duration: float
    focus_start_time: float
    focus_duration: float
    channel_indices: List[int]
    channel_colors: Dict[str, str]
    channel_offset: int
    visible_channels: int
    sensitivity: float
    annotations: List[Dict[str, Any]]
    timestamp: str

# Application constants
APP_NAME = "Clinical EEG Viewer"
APP_VERSION = "2.0.0"
SUPPORTED_FORMATS = ['.edf', '.bdf']
DEFAULT_VIEW_DURATION = 10.0
DEFAULT_SENSITIVITY = 50
DEFAULT_VISIBLE_CHANNELS = 10
AUTO_SAVE_INTERVAL_MS = 300000  # 5 minutes