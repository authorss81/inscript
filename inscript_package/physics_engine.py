"""physics_engine.py — Pure-Python 2D physics engine (Box2D-like API)

Provides PhysicsWorld, Body, Shape, Joint types.
Used by stdlib_values.py for native InScript struct wrapping.
"""
from __future__ import annotations
import math
from typing import Any, Callable, Dict, List, Optional, Tuple


# Constants
BODY_STATIC    = 0
BODY_DYNAMIC   = 1
BODY_KINEMATIC = 2

SHAPE_RECT     = 0
SHAPE_CIRCLE   = 1

JOINT_DISTANCE   = 0
JOINT_REVOLUTE   = 1
JOINT_PRISMATIC  = 2
JOINT_WELD       = 3
JOINT_MOUSE      = 4


# ── Vec2 helper ────────────────────────────────────────────────────────
class _Vec2:
    __slots__ = ("x", "y")
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x); self.y = float(y)
    def __add__(self, o): return _Vec2(self.x+o.x, self.y+o.y)
    def __sub__(self, o): return _Vec2(self.x-o.x, self.y-o.y)
    def __mul__(self, s): return _Vec2(self.x*s, self.y*s)
    def __neg__(self): return _Vec2(-self.x, -self.y)
    def __repr__(self): return f"({self.x:.2f},{self.y:.2f})"
    def length(self): return math.hypot(self.x, self.y)
    def length_sq(self): return self.x*self.x + self.y*self.y
    def normalized(self):
        l = self.length()
        if l == 0: return _Vec2(0, 0)
        return _Vec2(self.x/l, self.y/l)
    def dot(self, o): return self.x*o.x + self.y*o.y
    def cross(self, o): return self.x*o.y - self.y*o.x


# ── Shape ───────────────────────────────────────────────────────────────
class Shape:
    __slots__ = ("shape_type", "width", "height", "radius", "vertices")
    def __init__(self, shape_type: int, **kwargs):
        self.shape_type = shape_type
        self.width  = kwargs.get("width",  0.0)
        self.height = kwargs.get("height", 0.0)
        self.radius = kwargs.get("radius", 0.0)
        self.vertices = kwargs.get("vertices", [])

    @staticmethod
    def rect(w: float, h: float) -> Shape:
        return Shape(SHAPE_RECT, width=float(w), height=float(h))

    @staticmethod
    def circle(r: float) -> Shape:
        return Shape(SHAPE_CIRCLE, radius=float(r))

    def get_attr(self, name: str) -> Any:
        if name == "shape_type": return self.shape_type
        if name == "width": return self.width
        if name == "height": return self.height
        if name == "radius": return self.radius
        raise AttributeError(name)

    def set_attr(self, name: str, val: Any):
        raise AttributeError(name)


# ── Body ────────────────────────────────────────────────────────────────
class Body:
    __slots__ = (
        "shape", "body_type", "mass", "invmass", "density",
        "x", "y", "vx", "vy", "restitution", "friction",
        "tag", "_alive", "_prev_x", "_prev_y",
    )
    def __init__(self, shape: Shape, body_type: int = BODY_DYNAMIC, mass: float = 1.0, tag: str = ""):
        self.shape = shape
        self.body_type = body_type
        self.density = 1.0
        self.mass = float(mass) if body_type == BODY_DYNAMIC else 0.0
        self.invmass = 1.0 / self.mass if self.mass > 0 else 0.0
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.restitution = 0.3
        self.friction = 0.5
        self.tag = str(tag)
        self._alive = True
        self._prev_x = 0.0
        self._prev_y = 0.0

    @property
    def is_static(self) -> bool: return self.body_type == BODY_STATIC
    @property
    def is_dynamic(self) -> bool: return self.body_type == BODY_DYNAMIC
    @property
    def is_kinematic(self) -> bool: return self.body_type == BODY_KINEMATIC

    def get_attr(self, name: str) -> Any:
        if name == "x": return self.x
        if name == "y": return self.y
        if name == "vx": return self.vx
        if name == "vy": return self.vy
        if name == "mass": return self.mass
        if name == "density": return self.density
        if name == "restitution": return self.restitution
        if name == "friction": return self.friction
        if name == "body_type": return self.body_type
        if name == "tag": return self.tag
        if name == "is_static": return self.is_static
        if name == "is_dynamic": return self.is_dynamic
        if name == "is_kinematic": return self.is_kinematic
        if name == "apply_force": return self.apply_force
        if name == "apply_impulse": return self.apply_impulse
        if name == "apply_force_to_center": return self.apply_force_to_center
        if name == "get_position": return self.get_position
        if name == "set_position": return self.set_position
        if name == "get_velocity": return self.get_velocity
        if name == "set_velocity": return self.set_velocity
        if name == "set_transform": return self.set_transform
        raise AttributeError(name)

    def set_attr(self, name: str, val: Any):
        if name == "x": self.x = float(val)
        elif name == "y": self.y = float(val)
        elif name == "vx": self.vx = float(val)
        elif name == "vy": self.vy = float(val)
        elif name == "mass":
            self.mass = float(val)
            self.invmass = 1.0 / self.mass if self.mass > 0 else 0.0
        elif name == "density":
            self.density = float(val)
        elif name == "restitution": self.restitution = float(val)
        elif name == "friction": self.friction = float(val)
        elif name == "body_type": self.body_type = int(val)
        elif name == "tag": self.tag = str(val)
        else: raise AttributeError(name)

    def apply_force(self, fx: float, fy: float):
        if self.is_dynamic and self.mass > 0:
            self.vx += fx / self.mass
            self.vy += fy / self.mass

    def apply_impulse(self, ix: float, iy: float):
        if self.is_dynamic and self.mass > 0:
            self.vx += ix / self.mass
            self.vy += iy / self.mass

    def apply_force_to_center(self, fx: float, fy: float):
        self.apply_force(fx, fy)

    def get_position(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def set_position(self, x: float, y: float):
        self.x = float(x)
        self.y = float(y)

    def get_velocity(self) -> Tuple[float, float]:
        return (self.vx, self.vy)

    def set_velocity(self, vx: float, vy: float):
        self.vx = float(vx)
        self.vy = float(vy)

    def set_transform(self, x: float, y: float):
        self.set_position(x, y)


# ── Joint ───────────────────────────────────────────────────────────────
class Joint:
    __slots__ = (
        "joint_type", "body_a", "body_b",
        "anchor_x", "anchor_y",
        "anchor_a_x", "anchor_a_y", "anchor_b_x", "anchor_b_y",
        "length", "stiffness", "damping",
        "lower_angle", "upper_angle", "enable_motor", "motor_speed",
        "max_motor_torque", "axis_x", "axis_y",
        "lower_limit", "upper_limit", "max_force",
    )
    def __init__(self, joint_type: int, body_a: Body, body_b: Body, **kwargs):
        self.joint_type = joint_type
        self.body_a = body_a
        self.body_b = body_b
        self.anchor_x = kwargs.get("anchor_x", 0.0)
        self.anchor_y = kwargs.get("anchor_y", 0.0)
        self.anchor_a_x = kwargs.get("anchor_a_x", 0.0)
        self.anchor_a_y = kwargs.get("anchor_a_y", 0.0)
        self.anchor_b_x = kwargs.get("anchor_b_x", 0.0)
        self.anchor_b_y = kwargs.get("anchor_b_y", 0.0)
        self.length = kwargs.get("length", 1.0)
        self.stiffness = kwargs.get("stiffness", 1.0)
        self.damping = kwargs.get("damping", 0.0)
        self.lower_angle = kwargs.get("lower_angle", -math.pi)
        self.upper_angle = kwargs.get("upper_angle",  math.pi)
        self.enable_motor = kwargs.get("enable_motor", False)
        self.motor_speed = kwargs.get("motor_speed", 0.0)
        self.max_motor_torque = kwargs.get("max_motor_torque", 0.0)
        self.axis_x = kwargs.get("axis_x", 0.0)
        self.axis_y = kwargs.get("axis_y", 1.0)
        self.lower_limit = kwargs.get("lower_limit", 0.0)
        self.upper_limit = kwargs.get("upper_limit", 0.0)
        self.max_force = kwargs.get("max_force", 1000.0)


    def get_attr(self, name: str) -> Any:
        if name == "joint_type": return self.joint_type
        if name == "body_a": return self.body_a
        if name == "body_b": return self.body_b
        if name == "anchor_x": return self.anchor_x
        if name == "anchor_y": return self.anchor_y
        if name == "anchor_a_x": return self.anchor_a_x
        if name == "anchor_a_y": return self.anchor_a_y
        if name == "anchor_b_x": return self.anchor_b_x
        if name == "anchor_b_y": return self.anchor_b_y
        if name == "length": return self.length
        if name == "stiffness": return self.stiffness
        if name == "damping": return self.damping
        raise AttributeError(name)


# ── Contact point ──────────────────────────────────────────────────────
class Contact:
    __slots__ = ("body_a", "body_b", "normal_x", "normal_y", "point_x", "point_y", "penetration")
    def __init__(self, body_a: Body, body_b: Body,
                 nx: float = 0.0, ny: float = 0.0,
                 px: float = 0.0, py: float = 0.0,
                 pen: float = 0.0):
        self.body_a = body_a
        self.body_b = body_b
        self.normal_x = nx
        self.normal_y = ny
        self.point_x = px
        self.point_y = py
        self.penetration = pen

    def get_attr(self, name: str) -> Any:
        if name == "body_a": return self.body_a
        if name == "body_b": return self.body_b
        if name == "normal_x": return self.normal_x
        if name == "normal_y": return self.normal_y
        if name == "point_x": return self.point_x
        if name == "point_y": return self.point_y
        if name == "penetration": return self.penetration
        raise AttributeError(name)


# ── PhysicsWorld (the main simulation) ──────────────────────────────────
class PhysicsWorld:
    def __init__(self, gravity_x: float = 0.0, gravity_y: float = 500.0):
        self._gx = float(gravity_x)
        self._gy = float(gravity_y)
        self._bodies: List[Body] = []
        self._joints: List[Joint] = []
        self._begin_contact_cb: Optional[Callable] = None
        self._end_contact_cb: Optional[Callable] = None
        self._pre_solve_cb: Optional[Callable] = None
        self._collision_pairs: set = set()

    @property
    def gravity_x(self) -> float: return self._gx
    @gravity_x.setter
    def gravity_x(self, v: float): self._gx = float(v)

    @property
    def gravity_y(self) -> float: return self._gy
    @gravity_y.setter
    def gravity_y(self, v: float): self._gy = float(v)

    def create_body(self, shape, body_type: int = BODY_DYNAMIC, mass: float = 1.0, tag: str = "", x: float = 0.0, y: float = 0.0, density: float = 1.0) -> Body:
        if density != 1.0 and body_type == BODY_DYNAMIC:
            area = (shape.width * shape.height) if shape.shape_type == SHAPE_RECT else (3.14159 * shape.radius ** 2)
            mass = area * density if area > 0 else mass
        b = Body(shape, body_type, mass, tag)
        b.density = density
        b.x = float(x)
        b.y = float(y)
        b._prev_x = b.x
        b._prev_y = b.y
        self._bodies.append(b)
        return b

    def destroy_body(self, body: Body):
        if body in self._bodies:
            self._bodies.remove(body)
            body._alive = False

    def create_joint(self, joint_type: int, body_a: Body, body_b: Body, **kwargs) -> Joint:
        j = Joint(joint_type, body_a, body_b, **kwargs)
        self._joints.append(j)
        return j

    def destroy_joint(self, joint: Joint):
        if joint in self._joints:
            self._joints.remove(joint)

    # ── Collision callbacks ──────────────────────────────────────────
    def on_begin_contact(self, cb: Callable):
        self._begin_contact_cb = cb

    def on_end_contact(self, cb: Callable):
        self._end_contact_cb = cb

    def on_pre_solve(self, cb: Callable):
        self._pre_solve_cb = cb

    # ── Step ──────────────────────────────────────────────────────────
    def step(self, dt: float):
        dt = float(dt)
        dynamics = [b for b in self._bodies if b.is_dynamic and b._alive]
        all_bodies = [b for b in self._bodies if b._alive]

        # Save previous positions for kinematic velocity calc
        for b in dynamics:
            b._prev_x = b.x
            b._prev_y = b.y

        # Apply gravity
        for b in dynamics:
            b.vx += self._gx * dt
            b.vy += self._gy * dt

        # Apply joint forces (simple spring for distance joint)
        for j in self._joints:
            self._solve_joint(j)

        # Integrate positions
        for b in dynamics:
            b.x += b.vx * dt
            b.y += b.vy * dt

        # Kinematic bodies: compute velocity from position delta
        for b in all_bodies:
            if b.body_type == BODY_KINEMATIC:
                b.vx = (b.x - b._prev_x) / dt if dt > 0 else 0
                b.vy = (b.y - b._prev_y) / dt if dt > 0 else 0

        # Detect collisions
        new_pairs: set = set()
        for i in range(len(all_bodies)):
            for j_idx in range(i + 1, len(all_bodies)):
                a, b_body = all_bodies[i], all_bodies[j_idx]
                if a.is_static and b_body.is_static:
                    continue
                contact = self._detect_collision(a, b_body)
                if contact:
                    pair = (id(a), id(b_body))
                    new_pairs.add(pair)
                    reversed_pair = (id(b_body), id(a))

                    # Allow callback to disable collision
                    if self._pre_solve_cb:
                        result = self._pre_solve_cb(a, b_body, contact)
                        if result is False:
                            continue

                    # Resolve collision
                    self._resolve_collision(contact)

                    # Fire begin contact
                    if pair not in self._collision_pairs and self._begin_contact_cb:
                        self._begin_contact_cb(a, b_body, contact)

        # Fire end contact for pairs that separated
        for pair in self._collision_pairs:
            if pair not in new_pairs:
                a_id, b_id = pair
                a_body = next((b for b in all_bodies if id(b) == a_id), None)
                b_body_obj = next((b for b in all_bodies if id(b) == b_id), None)
                if a_body and b_body_obj and self._end_contact_cb:
                    self._end_contact_cb(a_body, b_body_obj)

        self._collision_pairs = new_pairs

        # Damping for stability
        for b in dynamics:
            b.vx *= 0.99
            b.vy *= 0.99

    # ── Collision detection ──────────────────────────────────────────
    def _get_aabb(self, body: Body) -> Tuple[float, float, float, float]:
        s = body.shape
        if s.shape_type == SHAPE_RECT:
            hw, hh = s.width / 2, s.height / 2
            return (body.x - hw, body.y - hh, body.x + hw, body.y + hh)
        elif s.shape_type == SHAPE_CIRCLE:
            r = s.radius
            return (body.x - r, body.y - r, body.x + r, body.y + r)
        return (body.x, body.y, body.x, body.y)

    def _detect_collision(self, a: Body, b: Body) -> Optional[Contact]:
        sa, sb = a.shape, b.shape
        if sa.shape_type == SHAPE_RECT and sb.shape_type == SHAPE_RECT:
            return self._rect_vs_rect(a, b)
        elif sa.shape_type == SHAPE_CIRCLE and sb.shape_type == SHAPE_CIRCLE:
            return self._circle_vs_circle(a, b)
        elif sa.shape_type == SHAPE_RECT and sb.shape_type == SHAPE_CIRCLE:
            return self._rect_vs_circle(a, b)
        elif sa.shape_type == SHAPE_CIRCLE and sb.shape_type == SHAPE_RECT:
            return self._rect_vs_circle(b, a)
        return None

    def _rect_vs_rect(self, a: Body, b: Body) -> Optional[Contact]:
        ax1, ay1, ax2, ay2 = self._get_aabb(a)
        bx1, by1, bx2, by2 = self._get_aabb(b)
        if not (ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1):
            return None
        overlap_x = min(ax2 - bx1, bx2 - ax1)
        overlap_y = min(ay2 - by1, by2 - ay1)
        if overlap_x < overlap_y:
            nx = -1.0 if a.x < b.x else 1.0
            ny = 0.0
            pen = overlap_x
        else:
            nx = 0.0
            ny = -1.0 if a.y < b.y else 1.0
            pen = overlap_y
        px = (a.x + b.x) / 2
        py = (a.y + b.y) / 2
        return Contact(a, b, nx, ny, px, py, pen)

    def _circle_vs_circle(self, a: Body, b: Body) -> Optional[Contact]:
        dx = b.x - a.x
        dy = b.y - a.y
        dist = math.hypot(dx, dy)
        rad_sum = a.shape.radius + b.shape.radius
        if dist >= rad_sum or dist == 0:
            return None
        nx = dx / dist if dist > 0 else 1.0
        ny = dy / dist if dist > 0 else 0.0
        pen = rad_sum - dist
        px = (a.x + b.x) / 2
        py = (a.y + b.y) / 2
        return Contact(a, b, nx, ny, px, py, pen)

    def _rect_vs_circle(self, rect: Body, circle: Body) -> Optional[Contact]:
        ax1, ay1, ax2, ay2 = self._get_aabb(rect)
        cx, cy = circle.x, circle.y
        closest_x = max(ax1, min(cx, ax2))
        closest_y = max(ay1, min(cy, ay2))
        dx = cx - closest_x
        dy = cy - closest_y
        dist_sq = dx*dx + dy*dy
        r = circle.shape.radius
        if dist_sq >= r*r:
            return None
        dist = math.sqrt(dist_sq) if dist_sq > 0 else 1
        nx = dx / dist if dist_sq > 0 else -1.0
        ny = dy / dist if dist_sq > 0 else 0.0
        pen = r - dist
        return Contact(rect, circle, nx, ny, (cx + rect.x) / 2, (cy + rect.y) / 2, pen)

    # ── Collision resolution ─────────────────────────────────────────
    def _resolve_collision(self, c: Contact):
        a, b = c.body_a, c.body_b
        if a.is_static and b.is_static:
            return
        invmass_sum = a.invmass + b.invmass
        if invmass_sum == 0:
            return
        nx, ny = c.normal_x, c.normal_y
        rel_vx = a.vx - b.vx
        rel_vy = a.vy - b.vy
        rel_vn = rel_vx * nx + rel_vy * ny
        if rel_vn > 0:
            rel_vn = 0
        e = min(a.restitution, b.restitution)
        j = -(1 + e) * rel_vn / invmass_sum
        a.vx += j * a.invmass * nx
        a.vy += j * a.invmass * ny
        b.vx -= j * b.invmass * nx
        b.vy -= j * b.invmass * ny
        # Friction impulse (tangential, opposes relative motion)
        tnx, tny = -ny, nx
        rel_vt = rel_vx * tnx + rel_vy * tny
        friction = (a.friction + b.friction) * 0.5
        max_friction = abs(j) * friction
        if abs(rel_vt) > 0 and invmass_sum > 0:
            jt_desired = -rel_vt / invmass_sum
            jt = max(-max_friction, min(jt_desired, max_friction))
            a.vx += jt * a.invmass * tnx
            a.vy += jt * a.invmass * tny
            b.vx -= jt * b.invmass * tnx
            b.vy -= jt * b.invmass * tny
        # Position correction
        correction = max(c.penetration - 0.01, 0.0)
        correction_factor = 0.8
        correction_val = correction * correction_factor / invmass_sum
        a.x += correction_val * a.invmass * nx
        a.y += correction_val * a.invmass * ny
        b.x -= correction_val * b.invmass * nx
        b.y -= correction_val * b.invmass * ny

    # ── Joint solving ────────────────────────────────────────────────
    def _solve_joint(self, j: Joint):
        if j.joint_type == JOINT_DISTANCE:
            dx = j.body_b.x - j.body_a.x
            dy = j.body_b.y - j.body_a.y
            dist = math.hypot(dx, dy)
            if dist == 0:
                return
            nx = dx / dist
            ny = dy / dist
            desired_dist = j.length
            diff = dist - desired_dist
            force_mag = -j.stiffness * diff - j.damping * ((j.body_b.vx - j.body_a.vx) * nx + (j.body_b.vy - j.body_a.vy) * ny)
            j.body_a.apply_force_to_center(-force_mag * nx, -force_mag * ny)
            j.body_b.apply_force_to_center(force_mag * nx, force_mag * ny)

        elif j.joint_type == JOINT_REVOLUTE:
            dx = j.body_b.x - j.body_a.x
            dy = j.body_b.y - j.body_a.y
            angle = math.atan2(dy, dx)
            if angle < j.lower_angle:
                correction = j.lower_angle - angle
                torque = j.stiffness * correction
                j.body_a.vx -= torque * 0.01 * math.cos(angle)
                j.body_a.vy -= torque * 0.01 * math.sin(angle)
            elif angle > j.upper_angle:
                correction = angle - j.upper_angle
                torque = j.stiffness * correction
                j.body_a.vx += torque * 0.01 * math.cos(angle)
                j.body_a.vy += torque * 0.01 * math.sin(angle)

        elif j.joint_type == JOINT_PRISMATIC:
            proj = (j.body_b.x - j.body_a.x) * j.axis_x + (j.body_b.y - j.body_a.y) * j.axis_y
            if proj < j.lower_limit:
                correction = j.lower_limit - proj
                j.body_a.apply_force_to_center(-j.stiffness * correction * j.axis_x,
                                                -j.stiffness * correction * j.axis_y)
                j.body_b.apply_force_to_center(j.stiffness * correction * j.axis_x,
                                                j.stiffness * correction * j.axis_y)

        elif j.joint_type == JOINT_WELD:
            dx = j.body_b.x - j.body_a.x
            dy = j.body_b.y - j.body_a.y
            dist = math.hypot(dx, dy)
            if dist > 0.01:
                nx = dx / dist
                ny = dy / dist
                force_mag = j.stiffness * dist - j.damping * ((j.body_b.vx - j.body_a.vx) * nx +
                                                              (j.body_b.vy - j.body_a.vy) * ny)
                j.body_a.apply_force_to_center(force_mag * nx, force_mag * ny)
                j.body_b.apply_force_to_center(-force_mag * nx, -force_mag * ny)

        elif j.joint_type == JOINT_MOUSE:
            dx = j.body_b.x - j.body_a.x
            dy = j.body_b.y - j.body_a.y
            dist = math.hypot(dx, dy)
            if dist > 0.01:
                nx = dx / dist
                ny = dy / dist
                force_mag = j.stiffness * dist - j.damping * (j.body_b.vx * nx + j.body_b.vy * ny)
                force_mag = min(force_mag, j.max_force)
                j.body_b.apply_force_to_center(force_mag * nx, force_mag * ny)

    def get_attr(self, name: str) -> Any:
        if name == "gravity_x": return self._gx
        if name == "gravity_y": return self._gy
        if name == "create_body": return self.create_body
        if name == "destroy_body": return self.destroy_body
        if name == "create_joint": return self.create_joint
        if name == "destroy_joint": return self.destroy_joint
        if name == "step": return self.step
        if name == "on_begin_contact": return self.on_begin_contact
        if name == "on_end_contact": return self.on_end_contact
        if name == "on_pre_solve": return self.on_pre_solve
        if name == "body_count": return self.body_count
        if name == "get_bodies": return self.get_bodies
        if name == "find_body_by_tag": return self.find_body_by_tag
        if name == "to_dict": return self.to_dict
        if name == "save_scene": return self.save_scene
        if name == "load_scene": return PhysicsWorld.load_scene
        if name == "create_character_body": return self.create_character_body
        if name == "character_body": return self.create_character_body
        raise AttributeError(name)

    def set_attr(self, name: str, val: Any):
        if name == "gravity_x": self._gx = float(val)
        elif name == "gravity_y": self._gy = float(val)
        else: raise AttributeError(name)

    # ── Query helpers ────────────────────────────────────────────────
    def body_count(self) -> int:
        return len(self._bodies)

    def get_bodies(self) -> List[Body]:
        return list(self._bodies)

    def find_body_by_tag(self, tag: str) -> Optional[Body]:
        for b in self._bodies:
            if b.tag == tag:
                return b
        return None

    def create_character_body(self, shape, tag: str = "", x: float = 0.0, y: float = 0.0,
                               one_way_platforms: bool = True) -> "CharacterBody":
        """Create a CharacterBody (dynamic body + character controller)."""
        b = self.create_body(shape, BODY_DYNAMIC, 1.0, tag, x, y)
        return CharacterBody(self, b, one_way_platforms=one_way_platforms)

    # ── Serialization ──────────────────────────────────────────────────
    def to_dict(self) -> dict:
        bodies = []
        for b in self._bodies:
            if not b._alive:
                continue
            if isinstance(b.shape, Shape):
                if b.shape.shape_type == SHAPE_RECT:
                    shape = {"type": "rect", "w": b.shape.width, "h": b.shape.height}
                else:
                    shape = {"type": "circle", "r": b.shape.radius}
            body = {
                "tag": b.tag, "body_type": b.body_type, "mass": b.mass,
                "density": b.density, "restitution": b.restitution,
                "friction": b.friction, "x": b.x, "y": b.y,
                "vx": b.vx, "vy": b.vy, "shape": shape,
            }
            bodies.append(body)
        joints = []
        for j in self._joints:
            joint = {
                "joint_type": j.joint_type,
                "body_a_tag": j.body_a.tag, "body_b_tag": j.body_b.tag,
                "length": getattr(j, 'length', 0),
                "stiffness": getattr(j, 'stiffness', 0),
                "damping": getattr(j, 'damping', 0),
            }
            joints.append(joint)
        return {"gravity_x": self._gx, "gravity_y": self._gy,
                "bodies": bodies, "joints": joints}

    def save_scene(self, path: str):
        import json
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load_scene(path: str, gravity_x: float = 0.0, gravity_y: float = 500.0) -> "PhysicsWorld":
        import json
        with open(path) as f:
            data = json.load(f)
        w = PhysicsWorld(data.get("gravity_x", gravity_x), data.get("gravity_y", gravity_y))
        tag_map = {}
        for bd in data.get("bodies", []):
            if bd["shape"]["type"] == "rect":
                shape = Shape.rect(bd["shape"]["w"], bd["shape"]["h"])
            else:
                shape = Shape.circle(bd["shape"]["r"])
            b = w.create_body(shape, bd["body_type"], bd["mass"], bd["tag"],
                              bd["x"], bd["y"], bd.get("density", 1.0))
            b.restitution = bd["restitution"]
            b.friction = bd["friction"]
            b.vx = bd.get("vx", 0.0)
            b.vy = bd.get("vy", 0.0)
            tag_map[bd["tag"]] = b
        for jd in data.get("joints", []):
            ba = tag_map.get(jd["body_a_tag"])
            bb = tag_map.get(jd["body_b_tag"])
            if ba and bb:
                w.create_joint(jd["joint_type"], ba, bb,
                               length=jd.get("length", 100.0),
                               stiffness=jd.get("stiffness", 1.0),
                               damping=jd.get("damping", 0.1))
        return w


# ═══════════════════════════════════════════════════════════════════════════
# v3.9.6.25 — CharacterBody: platformer character controller
# ═══════════════════════════════════════════════════════════════════════════

class CharacterBody:
    """Platformer character controller wrapping a Body.

    Usage:
        w = PhysicsWorld(0, 500)
        b = w.create_body(Shape.rect(16, 32), BODY_DYNAMIC, 1.0, "player")
        char = CharacterBody(w, b)
        char.move_and_slide(vel_x, vel_y)
        if char.is_on_floor(): ...
    """

    def __init__(self, world: "PhysicsWorld", body: Body, one_way_platforms: bool = True):
        self.world = world
        self.body = body
        self._floor = False
        self._wall = False
        self._ceiling = False
        self._floor_normal_x = 0.0
        self._floor_normal_y = 0.0
        self._wall_side = 0  # -1 left, 1 right, 0 none
        self._one_way_platforms = one_way_platforms
        self._platform_bodies: List[Body] = []
        self._knockback_x = 0.0
        self._knockback_y = 0.0
        self._slide_depth = 20  # max iteration depth

    def apply_knockback(self, ix: float, iy: float):
        self._knockback_x += float(ix)
        self._knockback_y += float(iy)

    def set_platforms(self, bodies: List[Body]):
        """Mark bodies as one-way platforms (collide only from above)."""
        self._platform_bodies = list(bodies)

    def move_and_slide(self, vx: float, vy: float, dt: float = 0.016):
        """Move character with collision resolution, updating floor/wall/ceiling state."""
        self._floor = False
        self._wall = False
        self._ceiling = False
        self._floor_normal_x = 0.0
        self._floor_normal_y = 0.0
        self._wall_side = 0

        total_vx = float(vx) + self._knockback_x
        total_vy = float(vy) + self._knockback_y
        self._knockback_x = 0.0
        self._knockback_y = 0.0

        dx = total_vx * dt
        dy = total_vy * dt

        remaining_x = dx
        remaining_y = dy
        iterations = 0
        max_iter = self._slide_depth
        # Always run at least one pass to resolve existing overlaps
        first_pass = True

        while (first_pass or abs(remaining_x) > 0.001 or abs(remaining_y) > 0.001) and iterations < max_iter:
            first_pass = False
            iterations += 1
            step_x = remaining_x
            step_y = remaining_y
            if step_x != 0 or step_y != 0:
                self.body.x += step_x
                self.body.y += step_y
            collision, hit = self._check_collision()

            if collision and hit is not None:
                nx, ny = hit.normal_x, hit.normal_y
                pen = hit.penetration

                # One-way platform check
                if self._one_way_platforms and hit.body_b in self._platform_bodies:
                    # Player above platform (ny < 0): standing or falling onto it → resolve
                    # Player below platform (ny > 0): jumping up into it → pass through
                    if ny > 0.5:
                        # Hitting from below — pass through
                        self.body.x -= step_x
                        self.body.y -= step_y
                        remaining_x = 0
                        remaining_y = 0
                        break
                    elif ny < -0.5 and step_y > 0:
                        # Moving upward into platform from below — pass through
                        self.body.x -= step_x
                        self.body.y -= step_y
                        remaining_x = 0
                        remaining_y = 0
                        break

                # Separate along collision normal
                self.body.x += nx * pen
                self.body.y += ny * pen

                # Update state
                if nx != 0:
                    self._wall = True
                    # nx < 0 means wall is on the right (push left), nx > 0 means wall is on the left
                    self._wall_side = -1 if nx > 0 else 1
                if ny < 0:
                    self._floor = True
                    self._floor_normal_x = nx
                    self._floor_normal_y = ny
                elif ny > 0:
                    self._ceiling = True

                # Consume velocity along normal, keep slide velocity
                if abs(nx) > abs(ny):
                    remaining_x = 0
                    remaining_y = step_y * (1 - abs(nx))
                else:
                    remaining_y = 0
                    if self._floor and step_x != 0 and abs(ny) > 0.7:
                        remaining_x = step_x * 0.3
                    else:
                        remaining_x = 0
            elif not collision:
                remaining_x -= step_x
                remaining_y -= step_y
                if abs(remaining_x) <= 0.001 and abs(remaining_y) <= 0.001:
                    break

    def move_and_collide(self, vx: float, vy: float, dt: float = 0.016) -> Optional[dict]:
        """Move and return first collision hit, or None. Does not auto-resolve."""
        dx = float(vx) * dt
        dy = float(vy) * dt
        self.body.x += dx
        self.body.y += dy
        _, hit = self._check_collision()
        if hit:
            self.body.x -= dx
            self.body.y -= dy
            return {
                "body": hit.body_b,
                "normal_x": hit.normal_x,
                "normal_y": hit.normal_y,
                "penetration": hit.penetration,
                "point_x": hit.point_x,
                "point_y": hit.point_y,
            }
        return None

    def is_on_floor(self) -> bool:
        return self._floor

    def is_on_wall(self) -> bool:
        return self._wall

    def is_on_ceiling(self) -> bool:
        return self._ceiling

    def get_floor_normal(self):
        return (self._floor_normal_x, self._floor_normal_y)

    def get_wall_side(self) -> int:
        return self._wall_side

    def _check_collision(self):
        """Check body vs all other bodies in world. Returns (hit: bool, Contact or None)."""
        for other in self.world._bodies:
            if other is self.body or not other._alive:
                continue
            c = self.world._detect_collision(self.body, other)
            if c is not None:
                return True, c
        return False, None
