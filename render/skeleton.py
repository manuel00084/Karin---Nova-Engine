"""GPU skinning skeleton — Bone hierarchy with local transforms (Babylon.js style)."""
import logging
import math
import numpy as np

_log = logging.getLogger("karin.skeleton")


def _yup_to_zup() -> np.ndarray:
    R = np.eye(4, dtype=np.float32)
    R[1, 1] = 0.0
    R[2, 2] = 0.0
    R[1, 2] = 1.0
    R[2, 1] = 1.0
    return R


def _quat_to_matrix(qx: float, qy: float, qz: float, qw: float) -> np.ndarray:
    m = np.eye(4, dtype=np.float32)
    m[0, 0] = 1 - 2*(qy*qy + qz*qz)
    m[0, 1] = 2*(qx*qy - qw*qz)
    m[0, 2] = 2*(qx*qz + qw*qy)
    m[1, 0] = 2*(qx*qy + qw*qz)
    m[1, 1] = 1 - 2*(qx*qx + qz*qz)
    m[1, 2] = 2*(qy*qz - qw*qx)
    m[2, 0] = 2*(qx*qz - qw*qy)
    m[2, 1] = 2*(qy*qz + qw*qx)
    m[2, 2] = 1 - 2*(qx*qx + qy*qy)
    return m


class Bone:
    """A single bone with local TRS, parent/children hierarchy (matches Babylon.js Bone API)."""

    def __init__(self, name: str, local_matrix: np.ndarray, inv_bind: np.ndarray, parent_idx: int = -1):
        self.name = name
        self.parent_idx = parent_idx
        self.children_indices: list[int] = []

        self._local_matrix = local_matrix.copy()
        self._inv_bind = inv_bind.copy()

        self._local_pos = local_matrix[0:3, 3].copy()
        self._local_scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self._local_rot = np.eye(4, dtype=np.float32)

    @property
    def local_matrix(self) -> np.ndarray:
        return self._local_matrix

    @local_matrix.setter
    def local_matrix(self, m: np.ndarray) -> None:
        self._local_matrix[:] = m

    def set_rotation_quaternion(self, qx: float, qy: float, qz: float, qw: float) -> None:
        rot = _quat_to_matrix(qx, qy, qz, qw)
        self._local_matrix[0:3, 0:3] = rot[0:3, 0:3]

    def set_position(self, x: float, y: float, z: float) -> None:
        self._local_matrix[0:3, 3] = [x, y, z]

    def get_position(self) -> np.ndarray:
        return self._local_matrix[0:3, 3].copy()

    def get_rotation_matrix(self) -> np.ndarray:
        r = np.eye(4, dtype=np.float32)
        r[0:3, 0:3] = self._local_matrix[0:3, 0:3]
        return r

    def decompose(self) -> tuple:
        pos = self._local_matrix[0:3, 3].copy()
        rot = np.eye(4, dtype=np.float32)
        rot[0:3, 0:3] = self._local_matrix[0:3, 0:3]
        return pos, rot

    def compose(self, pos: np.ndarray, rot: np.ndarray) -> None:
        self._local_matrix[0:3, 0:3] = rot[0:3, 0:3]
        self._local_matrix[0:3, 3] = pos

    def get_absolute_matrix(self, parent_world: np.ndarray | None) -> np.ndarray:
        if parent_world is not None:
            return parent_world @ self._local_matrix
        return self._local_matrix.copy()


class SkeletonSystem:
    """Reads glTF skeleton, builds bone hierarchy, computes skinning matrices via texture."""

    def __init__(self, glb_path: str = ''):
        self.num_joints = 0
        self.joint_data: np.ndarray | None = None
        self._bones: list[Bone] = []
        self._bone_map: dict[str, int] = {}
        self._index_to_name: dict[int, str] = {}
        self._world_matrices: list[np.ndarray] = []
        self._dirty = True
        self._gltf_skin_index = 0
        self._W_buf: np.ndarray | None = None
        self._IB_buf: np.ndarray | None = None
        self._mats_buf: np.ndarray | None = None
        self._Mx: np.ndarray | None = None
        self._MxB_buf: np.ndarray | None = None
        self._joint_transpose_buf: np.ndarray | None = None
        if glb_path:
            self._load_gltf(glb_path)

    @classmethod
    def from_pmx_data(cls, bone_names, bone_parents, bone_local_matrices, bone_inv_bind):
        skel = cls.__new__(cls)
        skel.num_joints = len(bone_names)
        skel.joint_data = None
        skel._bones = []
        skel._bone_map = {}
        skel._index_to_name = {}
        skel._world_matrices = []
        skel._dirty = True
        skel._gltf_skin_index = 0

        for i in range(skel.num_joints):
            name = bone_names[i]
            local = bone_local_matrices[i]
            inv_bind = bone_inv_bind[i]
            parent = bone_parents[i] if i != bone_parents[i] else -1
            bone = Bone(name, local.copy(), inv_bind.copy(), parent)
            skel._bones.append(bone)
            skel._bone_map[name] = i
            skel._index_to_name[i] = name

        for i, bone in enumerate(skel._bones):
            if bone.parent_idx >= 0:
                skel._bones[bone.parent_idx].children_indices.append(i)

        skel._world_matrices = [np.eye(4, dtype=np.float32) for _ in range(skel.num_joints)]
        skel._compute_world()
        skel._rebuild_texture()
        _log.info("PMX skeleton loaded: %d joints", skel.num_joints)
        return skel

    def _load_gltf(self, path: str) -> None:
        import pygltflib, os
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.vrm', '.vci'):
            gltf = pygltflib.GLTF2().load_binary(path)
        else:
            gltf = pygltflib.GLTF2().load(path)
        scene = gltf.scenes[gltf.scene]
        skins = gltf.skins
        if not skins:
            _log.warning("No skins in glTF")
            return

        skin = skins[0]
        joints = skin.joints
        self.num_joints = len(joints)

        ibm_idx = getattr(skin, "inverseBindMatrices", None)
        if ibm_idx is None:
            _log.warning("No inverseBindMatrices; using identity")
            inv_binds = np.tile(np.eye(4, dtype=np.float32), (self.num_joints, 1, 1))
        else:
            ibm_acc = gltf.accessors[ibm_idx]
            ibm_bv = gltf.binary_blob()
            ibm_bufv = gltf.bufferViews[ibm_acc.bufferView]
            start = ibm_bufv.byteOffset + (ibm_acc.byteOffset or 0)
            stride = ibm_bufv.byteStride or 16 * 4
            count = ibm_acc.count
            raw = np.frombuffer(ibm_bv, dtype=np.float32, offset=start, count=count * 16)
            inv_binds = raw.reshape(count, 4, 4).copy()
            inv_binds = inv_binds.transpose(0, 2, 1)

        # Map joint index → name
        joint_index_to_name: dict[int, str] = {}
        for i, jidx in enumerate(joints):
            node = gltf.nodes[jidx]
            joint_index_to_name[jidx] = node.name
            self._bone_map[node.name] = i
            self._index_to_name[i] = node.name

        # Build local bind matrices for each joint
        local_mats: dict[int, np.ndarray] = {}
        for root_idx in scene.nodes:
            self._build_local_mats(gltf, root_idx, np.eye(4, dtype=np.float32), local_mats)

        # Build hierarchy: find parent of each joint within the skin
        # A joint's parent is the nearest ancestor joint that is also in the skin
        joint_set = set(joints)
        node_parent: dict[int, int] = {}
        for root_idx in scene.nodes:
            self._build_parent_map(gltf, root_idx, -1, node_parent)
        parent_of_joint: dict[int, int] = {}
        for jidx in joints:
            p = node_parent.get(jidx, -1)
            while p >= 0 and p not in joint_set:
                p = node_parent.get(p, -1)
            parent_of_joint[jidx] = p if p >= 0 else -1

        # Convert glTF parent index → skin bone index
        parent_bone_of: dict[int, int] = {}
        for i, jidx in enumerate(joints):
            p_gltf = parent_of_joint.get(jidx, -1)
            if p_gltf in joint_index_to_name:
                p_name = joint_index_to_name[p_gltf]
                p_bone = self._bone_map.get(p_name, -1)
                parent_bone_of[i] = p_bone
            else:
                parent_bone_of[i] = -1

        # Build Bone objects
        self._bones = []
        for i, jidx in enumerate(joints):
            name = joint_index_to_name[jidx]
            local = local_mats.get(jidx, np.eye(4, dtype=np.float32))
            parent = parent_bone_of.get(i, -1)
            bone = Bone(name, local, inv_binds[i], parent)
            self._bones.append(bone)

        # Populate children
        for i, bone in enumerate(self._bones):
            if bone.parent_idx >= 0:
                self._bones[bone.parent_idx].children_indices.append(i)

        self._world_matrices = [np.eye(4, dtype=np.float32) for _ in range(self.num_joints)]
        self._compute_world()
        self._rebuild_texture()

        _log.info("Skeleton loaded: %d joints, %d bones mapped",
                  self.num_joints, len(self._bone_map))

    def _find_skin_parent(self, gltf, node_idx: int, joint_set: set) -> int | None:
        node = gltf.nodes[node_idx]
        for child_idx in (getattr(node, "children", None) or []):
            if child_idx in joint_set:
                return child_idx
        for child_idx in (getattr(node, "children", None) or []):
            result = self._find_skin_parent(gltf, child_idx, joint_set)
            if result is not None:
                return result
        return None

    def _find_parent_node(self, gltf, node_idx: int, joint_set: set) -> int | None:
        """Find the parent of node_idx that is in joint_set, walking up the tree."""
        parent_map: dict[int, int] = {}
        self._build_parent_map(gltf, gltf.scenes[gltf.scene].nodes[0], -1, parent_map)
        current = node_idx
        while current in parent_map and parent_map[current] >= 0:
            p = parent_map[current]
            if p in joint_set:
                return p
            current = p
        return None

    def _build_parent_map(self, gltf, node_idx: int, parent_idx: int, parent_map: dict) -> None:
        parent_map[node_idx] = parent_idx
        node = gltf.nodes[node_idx]
        for child_idx in (getattr(node, "children", None) or []):
            self._build_parent_map(gltf, child_idx, node_idx, parent_map)

    def _build_local_mats(self, gltf, node_idx: int, parent_mat: np.ndarray,
                          local_mats: dict) -> np.ndarray:
        node = gltf.nodes[node_idx]
        m = self._node_local_matrix(node)
        local_mats[node_idx] = m
        world = parent_mat @ m
        for child_idx in (getattr(node, "children", None) or []):
            self._build_local_mats(gltf, child_idx, world, local_mats)
        return world

    def _node_local_matrix(self, node) -> np.ndarray:
        if hasattr(node, "matrix") and node.matrix:
            raw = np.array(node.matrix, dtype=np.float32).reshape(4, 4)
            return raw.transpose()
        t = node.translation or [0, 0, 0]
        r = node.rotation or [0, 0, 0, 1]
        s = node.scale or [1, 1, 1]
        m = np.eye(4, dtype=np.float32)
        m[0:3, 3] = t
        qx, qy, qz, qw = r
        R = _quat_to_matrix(qx, qy, qz, qw)
        S = np.diag(s + [1.0])
        return m @ R @ S

    def _compute_world(self) -> None:
        """Walk hierarchy iteratively. First copy locals, then propagate parent transforms."""
        if not self._bones:
            return
        N = self.num_joints
        for i in range(N):
            self._world_matrices[i] = self._bones[i]._local_matrix.copy()
        for i in range(N):
            p = self._bones[i].parent_idx
            if p >= 0:
                self._world_matrices[i] = self._world_matrices[p] @ self._world_matrices[i]

    def _rebuild_texture(self) -> None:
        if self.num_joints == 0 or not self._world_matrices:
            return
        R = _yup_to_zup()
        N = self.num_joints
        W = np.zeros((N, 4, 4), dtype=np.float32)
        IB = np.zeros((N, 4, 4), dtype=np.float32)
        for i in range(N):
            W[i] = self._world_matrices[i]
            IB[i] = self._bones[i]._inv_bind
        try:
            from render.simd import fast_mat4_chain_mul, fast_mat4_batch_mul
            R2 = np.broadcast_to(R, (N, 4, 4)).copy()
            IBR = fast_mat4_batch_mul(IB, R2)
            img = fast_mat4_chain_mul(R, W, IBR)
            img = np.ascontiguousarray(img.transpose(1, 0, 2))
        except Exception:
            rows = []
            for i in range(N):
                skin_mat = R @ W[i] @ IB[i] @ R
                rows.append(skin_mat[0])
                rows.append(skin_mat[1])
                rows.append(skin_mat[2])
                rows.append(skin_mat[3])
            arr = np.array(rows, dtype=np.float32)
            img = arr.reshape(4, N, 4)
            img = np.ascontiguousarray(img.transpose(1, 0, 2))
        self.joint_data = img

    def set_bone_axis_angle(self, name: str, ax: float, ay: float, az: float, deg: float) -> None:
        """Set bone local rotation as axis-angle (glTF Y-up convention)."""
        bi = self._bone_map.get(name)
        if bi is None:
            _log.warning("Bone not found: %s", name)
            return
        rad = math.radians(deg)
        h = rad * 0.5
        s = math.sin(h)
        qx = ax * s
        qy = ay * s
        qz = az * s
        qw = math.cos(h)
        self.set_bone_rotation(name, qx, qy, qz, qw)

    def set_bone_rotation(self, name: str, qx: float, qy: float, qz: float, qw: float) -> None:
        """Set bone LOCAL rotation as quaternion. Hierarchy propagates on next update()."""
        bi = self._bone_map.get(name)
        if bi is None:
            _log.warning("Bone not found: %s", name)
            return
        self._set_bone_rotation_by_index(bi, qx, qy, qz, qw)

    def set_bone_rotation_by_index(self, bi: int, qx: float, qy: float, qz: float, qw: float) -> None:
        """Fast path: set bone rotation by bone index (no dict lookup)."""
        self._set_bone_rotation_by_index(bi, qx, qy, qz, qw)

    def _set_bone_rotation_by_index(self, bi: int, qx: float, qy: float, qz: float, qw: float) -> None:
        self._bones[bi].set_rotation_quaternion(qx, qy, qz, qw)
        self._dirty = True

    def set_bone_position(self, name: str, x: float, y: float, z: float) -> None:
        """Set bone LOCAL position. Hierarchy propagates on next update()."""
        bi = self._bone_map.get(name)
        if bi is None:
            _log.warning("Bone not found: %s", name)
            return
        self._bones[bi].set_position(x, y, z)
        self._dirty = True

    def set_bone_position_by_index(self, bi: int, x: float, y: float, z: float) -> None:
        """Fast path: set bone position by bone index (no dict lookup)."""
        self._bones[bi].set_position(x, y, z)
        self._dirty = True

    def get_bone_world_matrix(self, name: str) -> np.ndarray | None:
        """Get bone WORLD (absolute) matrix."""
        bi = self._bone_map.get(name)
        if bi is None:
            return None
        return self._world_matrices[bi].copy()

    def get_bone_local_matrix(self, name: str) -> np.ndarray | None:
        """Get bone LOCAL matrix (relative to parent)."""
        bi = self._bone_map.get(name)
        if bi is None:
            return None
        return self._bones[bi].local_matrix.copy()

    def get_bone_names(self) -> list[str]:
        return list(self._bone_map.keys())

    def get_joint_data(self, mirror_x: bool = False) -> np.ndarray:
        """Get skinning matrices as (num_joints, 4, 4) array for GPU upload.
        Used by Nova (wgpu) backend.
        Vertices are in Y-up (raw glTF), so skinning = R * world * inv_bind
        to yield Z-up world positions for the camera.
        If mirror_x, vertices are X-mirrored at load time. We need Mx * R * W * IB * Mx
        where Mx = diag(-1,1,1,1): right Mx undoes mirror before IB, left Mx re-mirrors result.
        """
        if self.num_joints == 0:
            return np.empty((0, 4, 4), dtype=np.float32)
        N = self.num_joints
        R = _yup_to_zup()
        if self._W_buf is None or self._W_buf.shape[0] < N:
            self._W_buf = np.zeros((N, 4, 4), dtype=np.float32)
            self._IB_buf = np.zeros((N, 4, 4), dtype=np.float32)
            self._mats_buf = np.zeros((N, 4, 4), dtype=np.float32)
        W = self._W_buf
        IB = self._IB_buf
        for i in range(N):
            W[i] = self._world_matrices[i]
            IB[i] = self._bones[i]._inv_bind
        try:
            from render.simd import fast_mat4_chain_mul, fast_mat4_batch_mul
            mats = fast_mat4_chain_mul(R, W, IB)
            if mirror_x:
                if self._Mx is None:
                    self._Mx = np.diag([-1.0, 1.0, 1.0, 1.0]).astype(np.float32)
                if self._MxB_buf is None or self._MxB_buf.shape[0] < N:
                    self._MxB_buf = np.broadcast_to(self._Mx, (N, 4, 4)).copy()
                MxB = self._MxB_buf
                mats = fast_mat4_batch_mul(MxB, mats)
                mats = fast_mat4_batch_mul(mats, MxB)
            return mats
        except Exception:
            mats = self._mats_buf
            for i in range(N):
                mats[i] = R @ W[i] @ IB[i]
            if mirror_x:
                if self._Mx is None:
                    self._Mx = np.diag([-1.0, 1.0, 1.0, 1.0]).astype(np.float32)
                for i in range(N):
                    mats[i] = self._Mx @ mats[i] @ self._Mx
            return mats

    def get_local_transforms_flat(self) -> np.ndarray:
        N = self.num_joints
        arr = np.zeros((N * 16,), dtype=np.float32)
        for i, bone in enumerate(self._bones):
            arr[i*16:(i+1)*16] = bone._local_matrix.flatten()
        return arr

    def get_parent_indices(self) -> np.ndarray:
        N = self.num_joints
        arr = np.full((N,), 0xFFFFFFFF, dtype=np.uint32)
        for i, bone in enumerate(self._bones):
            if bone.parent_idx >= 0:
                arr[i] = bone.parent_idx
        return arr

    def get_inv_bind_flat(self) -> np.ndarray:
        N = self.num_joints
        arr = np.zeros((N * 16,), dtype=np.float32)
        for i, bone in enumerate(self._bones):
            arr[i*16:(i+1)*16] = bone._inv_bind.flatten()
        return arr

    def update(self, skip_texture: bool = False) -> None:
        """Recompute world matrices from hierarchy, rebuild GPU texture. Call once per frame.
        If skip_texture=True, skips _rebuild_texture() (for GPU skinning compute path).
        """
        if not self._dirty:
            return
        self._compute_world()
        if not skip_texture:
            self._rebuild_texture()
        self._dirty = False
