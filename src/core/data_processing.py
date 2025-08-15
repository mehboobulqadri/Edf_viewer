"""
Core Data Processing Module
High-performance EDF data loading, caching, filtering, and signal processing.
"""

import gc
import logging
import mne
import numpy as np
import threading
import time
import weakref
from collections import deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
import pyqtgraph as pg

from config import PERF_CONFIG, NUMBA_AVAILABLE, CUPY_AVAILABLE, SUPPORTED_FORMATS
from utils.validation import ValidationUtils, ErrorHandlingUtils, DataValidator
from utils.performance import PerformanceUtils, MemoryOptimizer, PerformanceMonitor

# Conditional imports based on availability
if NUMBA_AVAILABLE:
    from numba import njit, prange

if CUPY_AVAILABLE:
    import cupy as cp

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: np.ndarray
    timestamp: float
    access_count: int
    size_bytes: int
    key: str

class DataLoaderThread(QThread):
    """Asynchronous data loading with progress reporting"""
    
    data_loaded = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self._cancel_requested = False
    
    def cancel(self):
        """Cancel the loading operation"""
        self._cancel_requested = True
    
    def run(self):
        """Load EDF file with comprehensive error handling"""
        try:
            # Validate file path
            is_valid, path = ValidationUtils.validate_file_path(
                self.file_path, SUPPORTED_FORMATS
            )
            
            if not is_valid:
                self.error_occurred.emit(f"Invalid file: {self.file_path}")
                return
            
            self.progress_updated.emit(10)
            
            if self._cancel_requested:
                return
            
            # Load EDF file with MNE
            logging.info(f"Loading EDF file: {self.file_path}")
            start_time = time.time()
            
            raw = mne.io.read_raw_edf(
                self.file_path, 
                preload=True, 
                verbose=False
            )
            
            self.progress_updated.emit(50)
            
            if self._cancel_requested:
                return
            
            # Validate EDF compatibility
            is_compatible, message = DataValidator.validate_edf_compatibility(raw)
            if not is_compatible:
                self.error_occurred.emit(f"EDF compatibility error: {message}")
                return
            
            self.progress_updated.emit(75)
            
            if self._cancel_requested:
                return
            
            # Apply basic filtering
            try:
                raw.filter(l_freq=0.1, h_freq=None, verbose=False)
                logging.info("Applied high-pass filter (0.1 Hz)")
            except Exception as e:
                logging.warning(f"Failed to apply filter: {e}")
            
            self.progress_updated.emit(100)
            
            load_time = time.time() - start_time
            logging.info(
                f"EDF file loaded successfully in {load_time:.2f}s: "
                f"{len(raw.ch_names)} channels, {raw.info['sfreq']}Hz, "
                f"{raw.n_times / raw.info['sfreq']:.1f}s duration"
            )
            
            self.data_loaded.emit(raw)
            
        except Exception as e:
            error_msg = f"Failed to load EDF file: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)

class HighPerformanceDataCache:
    """Ultra-high performance data cache with intelligent prefetching"""
    
    def __init__(self, max_size_mb: int = None):
        self.max_size_mb = max_size_mb or PERF_CONFIG.get('cache_size_mb', 2048)
        self.max_size_bytes = self.max_size_mb * 1024 * 1024
        
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_size_bytes = 0
        self.hit_count = 0
        self.miss_count = 0
        
        self._lock = threading.RLock()
        self.prefetch_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache_prefetch")
        
        # Predictive caching
        self.access_history = deque(maxlen=100)
        self.prediction_patterns = {}
        
        logging.info(f"Initialized high-performance cache: {self.max_size_mb}MB limit")
    
    def get(self, key: str) -> Optional[np.ndarray]:
        """Get data from cache with hit/miss tracking"""
        with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                entry.access_count += 1
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                
                self.hit_count += 1
                self._record_access(key)
                
                logging.debug(f"Cache hit: {key}")
                return entry.data.copy() if entry.data.size < 1000000 else entry.data
            else:
                self.miss_count += 1
                logging.debug(f"Cache miss: {key}")
                return None
    
    def put(self, key: str, data: np.ndarray, prefetch: bool = False) -> bool:
        """Store data in cache with automatic eviction"""
        if data is None or data.size == 0:
            return False
        
        data_size = data.nbytes
        
        # Skip caching if data is too large
        if data_size > self.max_size_bytes * 0.5:
            logging.warning(f"Data too large for cache: {data_size / (1024*1024):.1f}MB")
            return False
        
        with self._lock:
            # Remove existing entry if present
            if key in self.cache:
                self._remove_entry(key)
            
            # Evict entries if necessary
            while (self.current_size_bytes + data_size > self.max_size_bytes and 
                   len(self.cache) > 0):
                self._evict_lru_entry()
            
            # Create cache entry
            entry = CacheEntry(
                data=data,
                timestamp=time.time(),
                access_count=1,
                size_bytes=data_size,
                key=key
            )
            
            self.cache[key] = entry
            self.current_size_bytes += data_size
            
            if not prefetch:
                self._record_access(key)
                self._trigger_predictive_prefetch(key)
            
            logging.debug(
                f"Cache put: {key}, size: {data_size / (1024*1024):.1f}MB, "
                f"total: {self.current_size_bytes / (1024*1024):.1f}MB"
            )
            
            return True
    
    def _remove_entry(self, key: str):
        """Remove entry from cache"""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.current_size_bytes -= entry.size_bytes
    
    def _evict_lru_entry(self):
        """Evict least recently used entry"""
        if self.cache:
            # Remove the first (oldest) entry
            key, entry = self.cache.popitem(last=False)
            self.current_size_bytes -= entry.size_bytes
            logging.debug(f"Evicted LRU entry: {key}")
    
    def _record_access(self, key: str):
        """Record access for predictive caching"""
        self.access_history.append((key, time.time()))
    
    def _trigger_predictive_prefetch(self, key: str):
        """Trigger predictive prefetching based on access patterns"""
        if not PERF_CONFIG.get('predictive_caching', True):
            return
        
        # Simple pattern: if we access key A, predict we'll need key B
        # This is a simplified implementation - could be much more sophisticated
        try:
            # Look for patterns in access history
            recent_accesses = [k for k, _ in list(self.access_history)[-10:]]
            
            if len(recent_accesses) >= 2:
                current_pattern = tuple(recent_accesses[-2:])
                
                # Update pattern statistics
                if current_pattern not in self.prediction_patterns:
                    self.prediction_patterns[current_pattern] = {}
                
                # This would trigger prefetching of predicted next access
                # Implementation depends on specific use case
                
        except Exception as e:
            logging.debug(f"Predictive prefetch error: {e}")
    
    def prefetch_data(self, key: str, data_generator_func, *args, **kwargs):
        """Asynchronously prefetch data"""
        def prefetch_worker():
            try:
                if key not in self.cache:
                    data = data_generator_func(*args, **kwargs)
                    if data is not None:
                        self.put(key, data, prefetch=True)
                        logging.debug(f"Prefetched: {key}")
            except Exception as e:
                logging.error(f"Prefetch failed for {key}: {e}")
        
        self.prefetch_executor.submit(prefetch_worker)
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.current_size_bytes = 0
            self.hit_count = 0
            self.miss_count = 0
            logging.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0
            
            return {
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'size_mb': self.current_size_bytes / (1024 * 1024),
                'max_size_mb': self.max_size_mb,
                'entry_count': len(self.cache),
                'utilization': self.current_size_bytes / self.max_size_bytes
            }
    
    def cleanup(self):
        """Cleanup cache resources"""
        self.clear()
        self.prefetch_executor.shutdown(wait=True)
        logging.info("Cache cleanup completed")

class HighPerformanceSignalProcessor:
    """Ultra-fast signal processing with GPU acceleration support"""
    
    def __init__(self):
        self.use_gpu = CUPY_AVAILABLE and PERF_CONFIG.get('use_gpu', False)
        self.use_numba = NUMBA_AVAILABLE and PERF_CONFIG.get('use_jit', False)
        
        self.filter_cache = {}
        self.processing_stats = {
            'operations_count': 0,
            'total_processing_time': 0.0,
            'gpu_operations': 0,
            'cpu_operations': 0
        }
        
        logging.info(
            f"Signal processor initialized: "
            f"GPU={'enabled' if self.use_gpu else 'disabled'}, "
            f"Numba={'enabled' if self.use_numba else 'disabled'}"
        )
    
    def downsample_data(self, data: np.ndarray, target_points: int, 
                       method: str = "decimate") -> np.ndarray:
        """High-performance data downsampling"""
        if data.size <= target_points:
            return data
        
        start_time = time.time()
        
        try:
            if self.use_gpu and data.nbytes > 10 * 1024 * 1024:  # Use GPU for large data
                result = self._gpu_downsample(data, target_points, method)
                self.processing_stats['gpu_operations'] += 1
            elif self.use_numba:
                result = self._numba_downsample(data, target_points, method)
                self.processing_stats['cpu_operations'] += 1
            else:
                result = self._cpu_downsample(data, target_points, method)
                self.processing_stats['cpu_operations'] += 1
            
            processing_time = time.time() - start_time
            self.processing_stats['operations_count'] += 1
            self.processing_stats['total_processing_time'] += processing_time
            
            logging.debug(
                f"Downsampled {data.shape} -> {result.shape} in {processing_time:.3f}s "
                f"using {'GPU' if self.use_gpu and data.nbytes > 10 * 1024 * 1024 else 'CPU'}"
            )
            
            return result
            
        except Exception as e:
            logging.error(f"Downsampling failed: {e}")
            return self._cpu_downsample(data, target_points, method)
    
    def _cpu_downsample(self, data: np.ndarray, target_points: int, 
                       method: str = "decimate") -> np.ndarray:
        """CPU-based downsampling"""
        if method == "decimate":
            step = max(1, data.shape[-1] // target_points)
            return data[..., ::step]
        elif method == "average":
            # Block averaging for better visual quality
            block_size = data.shape[-1] // target_points
            if block_size > 1:
                n_blocks = data.shape[-1] // block_size
                reshaped = data[..., :n_blocks * block_size].reshape(
                    *data.shape[:-1], n_blocks, block_size
                )
                return np.mean(reshaped, axis=-1)
        elif method == "min_max":
            # Min-max downsampling for better visual representation
            step = max(1, data.shape[-1] // (target_points // 2))
            indices = np.arange(0, data.shape[-1] - step, step)
            
            result = np.empty((*data.shape[:-1], len(indices) * 2), dtype=data.dtype)
            
            for i, idx in enumerate(indices):
                block = data[..., idx:idx + step]
                result[..., i * 2] = np.min(block, axis=-1)
                result[..., i * 2 + 1] = np.max(block, axis=-1)
            
            return result
        
        # Default fallback
        step = max(1, data.shape[-1] // target_points)
        return data[..., ::step]
    
    def _gpu_downsample(self, data: np.ndarray, target_points: int, 
                       method: str = "decimate") -> np.ndarray:
        """GPU-based downsampling using CuPy"""
        if not CUPY_AVAILABLE:
            return self._cpu_downsample(data, target_points, method)
        
        try:
            # Transfer to GPU
            gpu_data = cp.asarray(data)
            
            if method == "decimate":
                step = max(1, data.shape[-1] // target_points)
                result_gpu = gpu_data[..., ::step]
            elif method == "average":
                block_size = data.shape[-1] // target_points
                if block_size > 1:
                    n_blocks = data.shape[-1] // block_size
                    reshaped = gpu_data[..., :n_blocks * block_size].reshape(
                        *data.shape[:-1], n_blocks, block_size
                    )
                    result_gpu = cp.mean(reshaped, axis=-1)
                else:
                    step = max(1, data.shape[-1] // target_points)
                    result_gpu = gpu_data[..., ::step]
            else:
                # Default to decimation on GPU
                step = max(1, data.shape[-1] // target_points)
                result_gpu = gpu_data[..., ::step]
            
            # Transfer back to CPU
            return cp.asnumpy(result_gpu)
            
        except Exception as e:
            logging.warning(f"GPU downsampling failed, falling back to CPU: {e}")
            return self._cpu_downsample(data, target_points, method)
    
    def _numba_downsample(self, data: np.ndarray, target_points: int, 
                         method: str = "decimate") -> np.ndarray:
        """Numba-accelerated downsampling"""
        if not NUMBA_AVAILABLE:
            return self._cpu_downsample(data, target_points, method)
        
        try:
            if method == "decimate":
                step = max(1, data.shape[-1] // target_points)
                return fast_decimate_numba(data, step)
            else:
                return self._cpu_downsample(data, target_points, method)
        except Exception as e:
            logging.warning(f"Numba downsampling failed, falling back to CPU: {e}")
            return self._cpu_downsample(data, target_points, method)
    
    def apply_filter(self, data: np.ndarray, filter_type: str, 
                    params: Dict[str, Any]) -> np.ndarray:
        """Apply various filters to EEG data"""
        cache_key = f"{filter_type}_{hash(str(sorted(params.items())))}"
        
        if cache_key in self.filter_cache:
            filter_coeffs = self.filter_cache[cache_key]
        else:
            filter_coeffs = self._create_filter(filter_type, params)
            self.filter_cache[cache_key] = filter_coeffs
        
        # Apply filter using scipy or custom implementation
        # This is a simplified version - real implementation would be more sophisticated
        try:
            if filter_type == "highpass":
                # Simple high-pass filter implementation
                return self._apply_highpass(data, params.get('cutoff', 0.5))
            elif filter_type == "lowpass":
                # Simple low-pass filter implementation
                return self._apply_lowpass(data, params.get('cutoff', 40.0))
            elif filter_type == "bandpass":
                # Bandpass filter
                data = self._apply_highpass(data, params.get('low_cutoff', 0.5))
                data = self._apply_lowpass(data, params.get('high_cutoff', 40.0))
                return data
            else:
                logging.warning(f"Unknown filter type: {filter_type}")
                return data
        except Exception as e:
            logging.error(f"Filter application failed: {e}")
            return data
    
    def _create_filter(self, filter_type: str, params: Dict[str, Any]):
        """Create filter coefficients"""
        # This would create actual filter coefficients
        # Simplified for now
        return {'type': filter_type, 'params': params}
    
    def _apply_highpass(self, data: np.ndarray, cutoff: float) -> np.ndarray:
        """Simple high-pass filter"""
        # Simplified exponential moving average high-pass
        alpha = 0.99  # This would be calculated based on cutoff and sampling rate
        result = np.zeros_like(data)
        
        if data.ndim == 2:
            for ch in range(data.shape[0]):
                result[ch, 0] = data[ch, 0]
                for i in range(1, data.shape[1]):
                    result[ch, i] = alpha * (result[ch, i-1] + data[ch, i] - data[ch, i-1])
        else:
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * (result[i-1] + data[i] - data[i-1])
        
        return result
    
    def _apply_lowpass(self, data: np.ndarray, cutoff: float) -> np.ndarray:
        """Simple low-pass filter"""
        # Simplified exponential moving average low-pass
        alpha = 0.1  # This would be calculated based on cutoff and sampling rate
        result = np.zeros_like(data)
        
        if data.ndim == 2:
            for ch in range(data.shape[0]):
                result[ch, 0] = data[ch, 0]
                for i in range(1, data.shape[1]):
                    result[ch, i] = alpha * data[ch, i] + (1 - alpha) * result[ch, i-1]
        else:
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i-1]
        
        return result
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get signal processing statistics"""
        total_ops = self.processing_stats['operations_count']
        avg_time = (self.processing_stats['total_processing_time'] / total_ops 
                   if total_ops > 0 else 0.0)
        
        return {
            'total_operations': total_ops,
            'average_processing_time': avg_time,
            'gpu_operations': self.processing_stats['gpu_operations'],
            'cpu_operations': self.processing_stats['cpu_operations'],
            'gpu_usage_ratio': (self.processing_stats['gpu_operations'] / total_ops 
                               if total_ops > 0 else 0.0)
        }

# Numba-accelerated functions (if available)
if NUMBA_AVAILABLE:
    @njit(parallel=True, fastmath=True)
    def fast_decimate_numba(data, step):
        """Ultra-fast decimation using Numba JIT compilation"""
        if data.ndim == 2:
            result = np.empty((data.shape[0], (data.shape[1] - 1) // step + 1), dtype=data.dtype)
            for i in prange(data.shape[0]):
                for j in prange(result.shape[1]):
                    if j * step < data.shape[1]:
                        result[i, j] = data[i, j * step]
            return result
        else:
            result = np.empty(((data.shape[0] - 1) // step + 1,), dtype=data.dtype)
            for i in prange(result.shape[0]):
                if i * step < data.shape[0]:
                    result[i] = data[i * step]
            return result

class PerformanceManager:
    """Centralized performance monitoring and optimization"""
    
    def __init__(self, viewer_instance):
        self.viewer = weakref.ref(viewer_instance)
        self.monitor = PerformanceMonitor()
        
        # Performance metrics
        self.frame_times = deque(maxlen=60)  # Last 60 frames for FPS calculation
        self.last_update_time = time.time()
        self.update_requested = False
        
        # Adaptive quality settings
        self.current_quality = 1.0
        self.target_fps = PERF_CONFIG.get('target_fps', 60)
        self.adaptive_quality = PERF_CONFIG.get('adaptive_quality', True)
        
        # Performance timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_performance_display)
        self.update_timer.start(1000)  # Update every second
        
        # Start monitoring
        self.monitor.start_monitoring(interval=0.5)
        
        logging.info("Performance manager initialized")
    
    def request_update(self):
        """Request a performance-optimized update"""
        self.update_requested = True
    
    def record_frame_time(self, frame_time: float):
        """Record frame rendering time"""
        self.frame_times.append(frame_time)
        self.monitor.record_render_time(frame_time)
        
        # Adaptive quality adjustment
        if self.adaptive_quality and len(self.frame_times) >= 10:
            avg_frame_time = sum(list(self.frame_times)[-10:]) / 10
            current_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            
            if current_fps < self.target_fps * 0.8:  # Below 80% of target
                self.current_quality = max(0.1, self.current_quality * 0.9)
                logging.debug(f"Quality reduced to {self.current_quality:.2f}")
            elif current_fps > self.target_fps * 1.2:  # Above 120% of target
                self.current_quality = min(1.0, self.current_quality * 1.1)
                logging.debug(f"Quality increased to {self.current_quality:.2f}")
    
    def get_recommended_points(self, base_points: int) -> int:
        """Get recommended number of points based on current performance"""
        if self.adaptive_quality:
            return int(base_points * self.current_quality)
        return base_points
    
    def should_skip_frame(self) -> bool:
        """Determine if frame should be skipped for performance"""
        if len(self.frame_times) < 5:
            return False
        
        recent_avg = sum(list(self.frame_times)[-5:]) / 5
        current_fps = 1.0 / recent_avg if recent_avg > 0 else 0
        
        return current_fps < self.target_fps * 0.5  # Skip if below 50% of target
    
    def update_performance_display(self):
        """Update performance display in the viewer"""
        viewer = self.viewer()
        if not viewer:
            return
        
        try:
            # Calculate current FPS
            if len(self.frame_times) > 0:
                recent_frame_time = sum(list(self.frame_times)[-10:]) / min(10, len(self.frame_times))
                current_fps = 1.0 / recent_frame_time if recent_frame_time > 0 else 0
            else:
                current_fps = 0
            
            # Get memory info
            memory_info = MemoryOptimizer.get_memory_info()
            
            # Update status bar if it exists
            if hasattr(viewer, 'status_bar'):
                viewer.status_bar.update_fps(current_fps)
                viewer.status_bar.update_memory(memory_info['rss'])
            
            # Legacy status labels support
            if hasattr(viewer, 'status_fps_label'):
                color = "green" if current_fps > 30 else "orange" if current_fps > 15 else "red"
                viewer.status_fps_label.setText(f"<span style='color: {color}'>FPS: {current_fps:.1f}</span>")
            
            if hasattr(viewer, 'status_memory_label'):
                viewer.status_memory_label.setText(f"Memory: {memory_info['rss']:.1f}MB")
            
            # Check for memory pressure
            is_pressure, usage = MemoryOptimizer.check_memory_pressure()
            if is_pressure:
                logging.warning(f"High memory usage: {usage:.1f}%")
                # Trigger garbage collection if memory is high
                MemoryOptimizer.optimize_memory_usage()
            
        except Exception as e:
            logging.error(f"Performance display update failed: {e}")
    
    def cleanup(self):
        """Cleanup performance manager resources"""
        self.update_timer.stop()
        self.monitor.stop_monitoring()
        logging.info("Performance manager cleanup completed")

# Export all classes
__all__ = [
    'DataLoaderThread', 'HighPerformanceDataCache', 'HighPerformanceSignalProcessor',
    'PerformanceManager', 'CacheEntry'
]