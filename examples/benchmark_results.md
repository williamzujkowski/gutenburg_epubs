# Performance Benchmark Results

## Test Environment
- Python version: 3.11.2
- OS: posix - linux
- Test iterations: 3

## Summary

| Benchmark | Sync Avg | Async Avg | Speedup |
|-----------|----------|-----------|---------|
| Book Search | 4.82s | 1.57s | 3.07x |
| Download 5 Books | 14.26s | 3.18s | 4.48x |

## Detailed Results
### Book Search

#### Synchronous Performance
- Average: 4.82s
- Minimum: 4.21s
- Maximum: 5.63s
- Median: 4.61s
- Standard Deviation: 0.74s

#### Asynchronous Performance
- Average: 1.57s
- Minimum: 1.38s
- Maximum: 1.72s
- Median: 1.61s
- Standard Deviation: 0.17s

#### Speedup: 3.07x

### Download 5 Books

#### Synchronous Performance
- Average: 14.26s
- Minimum: 12.87s
- Maximum: 15.33s
- Median: 14.58s
- Standard Deviation: 1.26s

#### Asynchronous Performance
- Average: 3.18s
- Minimum: 2.95s
- Maximum: 3.53s
- Median: 3.06s
- Standard Deviation: 0.30s

#### Speedup: 4.48x