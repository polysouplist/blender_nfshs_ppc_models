# **Z3D file specs** #

| Offset | Length | Type | Name | Description | Comments |
| --- | --- | --- | --- | --- | --- |
| 0x0 | 0x4 | uint32_t | **header_size** | | |
| 0x4 | | | **header** | | |
| 0x8 | 0x4 | uint32_t | **num_meshes** | | |
| 0xC | | | **mesh** | | |

| Offset | Length | Type | Name | Description | Comments |
| --- | --- | --- | --- | --- | --- |
| 0x0 | 0x4 | uint32_t | **has_uv** | | |
| 0x4 | 0x4 | | **unknown** | | |
| 0x8 | 0x4 | uint32_t | **name_length** | | |
| 0xC | 0x1 | char[1] | **name** | | |
| 0x0 | 0x1 | | **padding** | | |
| 0x0 | 0x4 | uint32_t | **num_vrtx** | | |
| 0x0 | 0x4 | uint32_t | **num_plgn** | | |
