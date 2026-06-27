"""Minimal GPU pipeline test: renders red to offscreen texture and checks pixel."""
import wgpu
import wgpu.backends.wgpu_native  # noqa
import numpy as np

import anyio

async def main():
    adapter = await wgpu.gpu.request_adapter_async(power_preference="low-power")
    device = adapter.request_device(required_features=[])

    # Offscreen render target (bgra8unorm)
    tex = device.create_texture(
        size=(32, 32, 1), mip_level_count=1, sample_count=1,
        dimension=wgpu.TextureDimension.d2, format=wgpu.TextureFormat.bgra8unorm,
        usage=wgpu.TextureUsage.RENDER_ATTACHMENT | wgpu.TextureUsage.COPY_SRC,
    )
    view = tex.create_view()

    # Fullscreen triangle vertex shader
    vs_src = """
    @vertex
    fn vs_main(@builtin(vertex_index) vi: u32) -> @builtin(position) vec4f {
        let verts = array<vec2f, 3>(
            vec2f(-1.0, -1.0),
            vec2f( 3.0, -1.0),
            vec2f(-1.0,  3.0),
        );
        return vec4f(verts[vi], 0.0, 1.0);
    }
    """

    # Fragment shader: solid RED
    fs_src = """
    @fragment
    fn fs_main() -> @location(0) vec4f {
        return vec4f(1.0, 0.0, 0.0, 1.0);
    }
    """

    vs = device.create_shader_module(code=vs_src)
    fs = device.create_shader_module(code=fs_src)

    pipeline = device.create_render_pipeline(
        layout=device.create_pipeline_layout(bind_group_layouts=[]),
        vertex={"module": vs, "entry_point": "vs_main", "buffers": []},
        primitive={"topology": wgpu.PrimitiveTopology.triangle_list},
        fragment={"module": fs, "entry_point": "fs_main", "targets": [{"format": wgpu.TextureFormat.bgra8unorm}]},
    )

    encoder = device.create_command_encoder()
    pass_enc = encoder.begin_render_pass(
        color_attachments=[{"view": view, "load_op": wgpu.LoadOp.clear, "store_op": wgpu.StoreOp.store, "clear_value": (0, 0, 0, 1)}],
    )
    pass_enc.set_pipeline(pipeline)
    pass_enc.draw(3)
    pass_enc.end()
    device.queue.submit([encoder.finish()])

    # Read pixel at (16,16) — should be RED (in BGRA: r=255, g=0, b=0)
    buffer = device.create_buffer(size=4, usage=wgpu.BufferUsage.COPY_DST | wgpu.BufferUsage.MAP_READ)
    enc2 = device.create_command_encoder()
    enc2.copy_texture_to_buffer(
        {"texture": tex, "mip_level": 0, "origin": (16, 16, 0)},
        {"buffer": buffer, "bytes_per_row": 256, "rows_per_image": 1},
        (1, 1, 1),
    )
    device.queue.submit([enc2.finish()])
    device.queue.submit([])  # flush

    data = device.queue.read_buffer(buffer, buffer_offset=0, size=4)
    b, g, r, a = data[0], data[1], data[2], data[3]
    print(f"Pixel at (16,16): R={r} G={g} B={b} A={a} (BGRA bytes)")
    if r == 255 and g == 0 and b == 0:
        print("TEST PASSED: GPU renders RED correctly")
    else:
        print("TEST FAILED: expected RED (R=255), got something else")

if __name__ == "__main__":
    anyio.run(main)
