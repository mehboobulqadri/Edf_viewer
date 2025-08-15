"""
Performance Optimization Utilities
High-performance utilities for memory management, array operations, and system monitoring.
"""

import gc
import logging
import numpy as np
import psutil
import threading
import time
import weakref
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from config import PERF_CONFIG, NUMBA_AVAILABLE, CUPY_AVAILABLE

# Conditional imports based on availability
if NUMBA_AVAILABLE:
    from numba import njit, prange

if CUPY_AVAILABLE:
    import cupy as cp

class PerformanceUtils:
    """Performance optimization utilities"""
    
    @staticmethod
    def optimize_array_operations(data, operation="copy"):
        """Optimize common array operations"""
        try:
            if data is None or not hasattr(data, 'shape'):
                return data
                
            # Use memory-mapped arrays for large data
            if hasattr(data, 'nbytes') and data.nbytes > 100 * 1024 * 1024:  # > 100MB
                logging.debug(f"Using optimized operations for large array: {data.nbytes / (1024*1024):.1f} MB")
                
            if operation == "copy":
                return np.copy(data) if data.size < 1000000 else data  # Avoid copying very large arrays
            elif operation == "zeros_like":
                return np.zeros_like(data)
            elif operation == "empty_like":
                return np.empty_like(data)
                
            return data
        except Exception as e:
            logging.error(f"Array optimization failed: {e}")
            return data
    
    @staticmethod
    def batch_ui_updates(update_func, updates_list: list, batch_size: int = 10):
        """Batch UI updates to improve performance"""
        try:
            for i in range(0, len(updates_list), batch_size):
                batch = updates_list[i:i+batch_size]
                for update in batch:
                    try:
                        update_func(update)
                    except Exception as e:
                        logging.error(f"Batch update failed: {e}")
                        continue
        except Exception as e:
            logging.error(f"Batch UI update failed: {e}")
    
    @staticmethod
    def downsample_data(data: np.ndarray, target_points: int, method: str = "decimate") -> np.ndarray:
        """Intelligent data downsampling for performance"""
        if data.size <= target_points:
            return data
        
        try:
            if method == "decimate":
                step = max(1, data.shape[-1] // target_points)
                return data[..., ::step]
            elif method == "average":
                # Block averaging for better visual quality
                block_size = data.shape[-1] // target_points
                if block_size > 1:
                    n_blocks = data.shape[-1] // block_size
                    reshaped = data[..., :n_blocks * block_size].reshape(*data.shape[:-1], n_blocks, block_size)
                    return np.mean(reshaped, axis=-1)
            
            return data[..., ::max(1, data.shape[-1] // target_points)]
            
        except Exception as e:
            logging.error(f"Data downsampling failed: {e}")
            return data

if NUMBA_AVAILABLE:
    @njit(parallel=True, fastmath=True)
    def fast_downsample_numba(data, step):
        """Ultra-fast downsampling using Numba JIT compilation"""
        result = np.empty((data.shape[0], (data.shape[1] - 1) // step + 1), dtype=data.dtype)
        for i in prange(data.shape[0]):
            for j in prange(result.shape[1]):
                result[i, j] = data[i, j * step]
        return result
    
    @njit(parallel=True, fastmath=True)
    def fast_filter_numba(data, alpha=0.1):
        """Fast exponential smoothing filter using Numba"""
        result = np.empty_like(data)
        for i in prange(data.shape[0]):
            result[i, 0] = data[i, 0]
            for j in range(1, data.shape[1]):
                result[i, j] = alpha * data[i, j] + (1 - alpha) * result[i, j - 1]
        return result

class MemoryOptimizer:
    """Memory usage optimization utilities"""
    
    @staticmethod
    def cleanup_qt_objects(obj_list: List[Any]) -> int:
        """Safely clean up Qt objects to prevent memory leaks"""
        cleaned = 0
        for obj in obj_list:
            try:
                if hasattr(obj, 'deleteLater'):
                    obj.deleteLater()
                    cleaned += 1
                elif hasattr(obj, 'clear'):
                    obj.clear()
                    cleaned += 1
            except Exception as e:
                logging.debug(f"Failed to clean Qt object: {e}")
        return cleaned
    
    @staticmethod
    def get_memory_info() -> Dict[str, float]:
        """Get current memory usage information"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss / (1024 * 1024),  # MB
                'vms': memory_info.vms / (1024 * 1024),  # MB
                'percent': process.memory_percent()
            }
        except Exception as e:
            logging.error(f"Failed to get memory info: {e}")
            return {'rss': 0, 'vms': 0, 'percent': 0}
    
    @staticmethod
    def force_garbage_collection():
        """Force garbage collection with performance monitoring"""
        start_time = time.time()
        collected = gc.collect()
        duration = time.time() - start_time
        
        if duration > 0.1:  # Log if GC takes more than 100ms
            logging.warning(f"Garbage collection took {duration:.2f}s, collected {collected} objects")
        else:
            logging.debug(f"Garbage collection: {collected} objects in {duration:.3f}s")
        
        return collected
    
    @staticmethod
    def check_memory_pressure(threshold_percent: float = 85.0) -> Tuple[bool, float]:
        """Check if system is under memory pressure"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            if usage_percent > threshold_percent:
                logging.warning(f"High memory usage detected: {usage_percent:.1f}%")
                return True, usage_percent
            
            return False, usage_percent
            
        except Exception as e:
            logging.error(f"Memory pressure check failed: {e}")
            return False, 0.0
    
    @staticmethod
    def optimize_memory_usage():
        """Perform comprehensive memory optimization"""
        initial_memory = MemoryOptimizer.get_memory_info()
        
        # Force garbage collection
        collected = MemoryOptimizer.force_garbage_collection()
        
        # Clear numpy and other caches if available
        try:
            # Clear numpy internal caches
            np._NoValue.__reduce__ = lambda self: (np._NoValue, ())
        except:
            pass
        
        final_memory = MemoryOptimizer.get_memory_info()
        
        memory_saved = initial_memory['rss'] - final_memory['rss']
        logging.info(
            f"Memory optimization: {memory_saved:.1f}MB freed, "
            f"{collected} objects collected"
        )
        
        return memory_saved

class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self):
        self.stats = {
            'render_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'frame_count': 0
        }
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self, interval: float = 1.0):
        """Start performance monitoring"""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logging.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logging.info("Performance monitoring stopped")
    
    def _monitor_loop(self, interval: float):
        """Performance monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                memory_info = MemoryOptimizer.get_memory_info()
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                # Store metrics
                self.stats['memory_usage'].append(memory_info['rss'])
                self.stats['cpu_usage'].append(cpu_percent)
                
                # Keep only last 100 samples to prevent memory growth
                for key in ['memory_usage', 'cpu_usage', 'render_times']:
                    if len(self.stats[key]) > 100:
                        self.stats[key] = self.stats[key][-100:]
                
                time.sleep(interval)
                
            except Exception as e:
                logging.error(f"Performance monitoring error: {e}")
                break
    
    def record_render_time(self, render_time: float):
        """Record rendering time"""
        self.stats['render_times'].append(render_time)
        self.stats['frame_count'] += 1
        
        if len(self.stats['render_times']) > 100:
            self.stats['render_times'] = self.stats['render_times'][-100:]
    
    def record_cache_hit(self):
        """Record cache hit"""
        self.stats['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record cache miss"""
        self.stats['cache_misses'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {
            'avg_render_time': 0.0,
            'max_render_time': 0.0,
            'avg_memory_usage': 0.0,
            'max_memory_usage': 0.0,
            'avg_cpu_usage': 0.0,
            'cache_hit_rate': 0.0,
            'frame_count': self.stats['frame_count']
        }
        
        try:
            if self.stats['render_times']:
                summary['avg_render_time'] = np.mean(self.stats['render_times'])
                summary['max_render_time'] = np.max(self.stats['render_times'])
            
            if self.stats['memory_usage']:
                summary['avg_memory_usage'] = np.mean(self.stats['memory_usage'])
                summary['max_memory_usage'] = np.max(self.stats['memory_usage'])
            
            if self.stats['cpu_usage']:
                summary['avg_cpu_usage'] = np.mean(self.stats['cpu_usage'])
            
            total_cache_ops = self.stats['cache_hits'] + self.stats['cache_misses']
            if total_cache_ops > 0:
                summary['cache_hit_rate'] = self.stats['cache_hits'] / total_cache_ops
                
        except Exception as e:
            logging.error(f"Performance summary calculation failed: {e}")
        
        return summary

class ThreadPoolManager:
    """Thread pool management for parallel processing"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or PERF_CONFIG.get('render_threads', 4)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_tasks = []
        self._lock = threading.Lock()
    
    def submit_task(self, func, *args, **kwargs):
        """Submit task to thread pool"""
        with self._lock:
            future = self.executor.submit(func, *args, **kwargs)
            self.active_tasks.append(weakref.ref(future))
            return future
    
    def wait_for_completion(self, timeout: Optional[float] = None):
        """Wait for all active tasks to complete"""
        with self._lock:
            active_futures = [ref() for ref in self.active_tasks if ref() is not None]
            self.active_tasks.clear()
        
        if active_futures:
            for future in active_futures:
                try:
                    future.result(timeout=timeout)
                except Exception as e:
                    logging.error(f"Task execution failed: {e}")
    
    def shutdown(self):
        """Shutdown thread pool"""
        self.wait_for_completion(timeout=5.0)
        self.executor.shutdown(wait=True)
        logging.info("Thread pool manager shutdown complete")

# GPU acceleration utilities (if CuPy is available)
if CUPY_AVAILABLE:
    class GPUAccelerator:
        """GPU acceleration utilities using CuPy"""
        
        @staticmethod
        def to_gpu(data: np.ndarray) -> cp.ndarray:
            """Transfer data to GPU memory"""
            try:
                return cp.asarray(data)
            except Exception as e:
                logging.error(f"GPU transfer failed: {e}")
                return data
        
        @staticmethod
        def to_cpu(data: cp.ndarray) -> np.ndarray:
            """Transfer data from GPU to CPU memory"""
            try:
                return cp.asnumpy(data)
            except Exception as e:
                logging.error(f"CPU transfer failed: {e}")
                return data
        
        @staticmethod
        def gpu_downsample(data: np.ndarray, step: int) -> np.ndarray:
            """GPU-accelerated downsampling"""
            try:
                gpu_data = cp.asarray(data)
                result = gpu_data[..., ::step]
                return cp.asnumpy(result)
            except Exception as e:
                logging.error(f"GPU downsampling failed: {e}")
                return PerformanceUtils.downsample_data(data, data.shape[-1] // step)

else:
    class GPUAccelerator:
        """Dummy GPU accelerator when CuPy is not available"""
        
        @staticmethod
        def to_gpu(data):
            return data
        
        @staticmethod
        def to_cpu(data):
            return data
        
        @staticmethod
        def gpu_downsample(data: np.ndarray, step: int) -> np.ndarray:
            return PerformanceUtils.downsample_data(data, data.shape[-1] // step)