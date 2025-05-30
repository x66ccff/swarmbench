import time

import numpy as np
from scipy.optimize import linear_sum_assignment
from src.swarmenv.swarmbench.physics import Mesh

from random import Random


class Task:

    def __init__(self, seed=42):
        self.seed = seed
        self.rng = Random(seed)
        self.rewards = {}

    def reset(self, env):
        pass

    def is_done(self, env):
        return False

    def update(self, env, actions):
        pass

    def task_obs(self, agent):
        return {}

    def desc(self):
        return ''


def spread(env, x0, x1, y0, y1, rng, symbol='A'):
    used_positions = set()
    for name, _ in env.agents.items():
        while True:
            x = rng.randint(x0, x1)
            y = rng.randint(y0, y1)
            pos = (y, x)
            if pos not in used_positions and env.grid[y, x] == '.':
                used_positions.add(pos)
                agent_mesh = Mesh(pos, np.array([[symbol]], dtype=str), False, name=name)
                agent_mesh.place(env.grid, env.mesh_map)
                env.agent_meshes[name] = agent_mesh
                env.meshes.append(agent_mesh)
                break

class Transport(Task):

    boxes = [
        {
            'shape': [
                ['B', 'B', 'B', '.', '.'],
                ['B', 'B', 'B', '.', '.'],
                ['B', 'B', 'B', '.', '.'],
                ['.', 'B', 'B', 'B', 'B'],
            ],
            'pos': (-4, -5),
            'gap': ((-1, None), (-4, None)),
        },
        {
            'shape': [
                ['.', '.', 'B', 'B', 'B'],
                ['.', '.', 'B', 'B', 'B'],
                ['.', '.', 'B', 'B', 'B'],
                ['B', 'B', 'B', 'B', '.'],
            ],
            'pos': (-4, 0),
            'gap': ((-1, None), (None, 4)),
        },
        {
            'shape': [
                ['.', '.', '.', 'B'],
                ['.', '.', '.', 'B'],
                ['B', 'B', 'B', 'B'],
                ['B', 'B', 'B', 'B'],
                ['B', 'B', 'B', '.'],
            ],
            'pos': (0, -4),
            'gap': ((None, 4), (-1, None)),
        },
        {
            'shape': [
                ['B', 'B', 'B', '.'],
                ['B', 'B', 'B', 'B'],
                ['B', 'B', 'B', 'B'],
                ['.', '.', '.', 'B'],
                ['.', '.', '.', 'B'],
            ],
            'pos': (-5, -4),
            'gap': ((-4, None), (-1, None)),
        },
        {
            'shape': [
                ['B', '.', '.', '.'],
                ['B', '.', '.', '.'],
                ['B', 'B', 'B', 'B'],
                ['B', 'B', 'B', 'B'],
                ['.', 'B', 'B', 'B'],
            ],
            'pos': (0, 0),
            'gap': ((None, 4), (None, 1)),
        },
        {
            'shape': [
                ['.', 'B', 'B', 'B'],
                ['B', 'B', 'B', 'B'],
                ['B', 'B', 'B', 'B'],
                ['B', '.', '.', '.'],
                ['B', '.', '.', '.'],
            ],
            'pos': (-5, 0),
            'gap': ((-4, None), (None, 1)),
        },
        {
            'shape': [
                ['B', 'B', 'B', 'B', '.'],
                ['.', '.', 'B', 'B', 'B'],
                ['.', '.', 'B', 'B', 'B'],
                ['.', '.', 'B', 'B', 'B'],
            ],
            'pos': (0, 0),
            'gap': ((None, 1), (None, 4)),
        },
        {
            'shape': [
                ['.', 'B', 'B', 'B', 'B'],
                ['B', 'B', 'B', '.', '.'],
                ['B', 'B', 'B', '.', '.'],
                ['B', 'B', 'B', '.', '.'],
            ],
            'pos': (0, -5),
            'gap': ((None, 1), (-4, None)),
        }
    ]

    def __init__(self, seed=42):
        super().__init__(seed)
        self.escaped = set()
        self.score = 0
        self.rewards = {}
        self.prev_box = 0, 0
        self.box_mesh = None

    def reset(self, env):
        self.rewards = {agent: 0 for agent in env.agents.values()}
        self.escaped = set()
        box = self.rng.choice(Transport.boxes)
        self.box_mesh = Mesh(
        (
                (box['pos'][0] + env.grid.shape[0]) % env.grid.shape[0],
                (box['pos'][1] + env.grid.shape[1]) % env.grid.shape[1]
            ),
            np.array(box['shape'], dtype=str), False, name='B'
        )
        self.prev_box = box['pos']
        wall_shape = np.full_like(env.grid, 'W', dtype=str)
        wall_shape[1:-1, 1:-1] = '.'
        wall_shape[box['gap'][0][0]:box['gap'][0][1], box['gap'][1][0]:box['gap'][1][1]] = '.'

        wall_mesh = Mesh((0, 0), wall_shape, static=True, name='W')
        wall_mesh.place(env.grid, env.mesh_map)
        env.meshes.append(wall_mesh)
        self.box_mesh.place(env.grid, env.mesh_map)
        self.box_mesh.mass = 5
        env.meshes.append(self.box_mesh)

        spread(env, 1, env.width - 2, 1, env.height - 2, self.rng)
        self.score = 0

    def is_done(self, env):
        all_out = True
        for name, mesh in env.agent_meshes.items():
            y, x = mesh.pos
            if 0 <= y < env.height and 0 <= x < env.width:
                all_out = False
        return all_out

    def update(self, env, actions):
        for name, mesh in env.agent_meshes.items():
            if name in self.escaped:
                continue
            i, j = mesh.pos
            reward = 0
            if not (0 <= i < env.height and 0 <= j < env.width):
                self.escaped.add(name)
                self.score += (env.max_round - env.round) / env.max_round
                reward += 1
            if (
                    (0 < i < env.height - 1 and 0 < j < env.width - 1)
                    and (
                        ('W' in env.grid[i - 1:i + 2, j] and 'B' in env.grid[i - 1:i + 2, j])
                        or ('W' in env.grid[i, j - 1:j + 2] and 'B' in env.grid[i, j - 1:j + 2])
                    )
            ):
                reward -= 0.2
            else:
                reward += max(0.05 - min([abs(i - self.box_mesh.pos[0] - di) + abs(j - self.box_mesh.pos[0] - dj)
                                     for di in range(self.box_mesh.shape.shape[0]) for dj in range(self.box_mesh.shape.shape[1])
                                     if self.box_mesh.shape[di, dj] == 'B']) * 0.01, 0)
            if self.box_mesh.pos != self.prev_box:
                reward += 0.5
                self.prev_box = self.box_mesh.pos
            self.rewards[env.agents[name]] = reward

    def task_obs(self, agent):
        if agent is None:
            return {'score': self.score}
        return {}

    def desc(self):
        return (
            "The boundary of the map is surrounded by walls (denoted as W), with a gap leading to the outside of the map (denoted as '*'). The gap is blocked by an obstacle (denoted as B).\n"
            "The goal is to first locate the obstacle (B), then have five robots simultaneously push it through the exit, and finally escape to the outside of the map (denoted as '*')."
        )


class Flocking(Task):
    def __init__(self, seed=42):
        super().__init__()
        self.target_shape = None
        self.shape_desc = ''
        self.score = 0
        self.init_dis = 0
        self.cur_dis = 1e10
        self.rewards = {}
        self.prev_dis = {}

    def emd(self, grid):
        tgt = np.argwhere(self.target_shape == 'A')  # shape (n,2)
        src = np.argwhere(grid == 'A')  # shape (m,2)
        n, m = len(tgt), len(src)
        if n == 0:
            return 0, 0, 0

        # D_x[i,j] = src[i,0] - tgt[j,0], D_y[i,j] = src[i,1] - tgt[j,1]
        D_x = src[:, 0:1] - tgt[:, 0]  # shape (m,n)
        D_y = src[:, 1:2] - tgt[:, 1]  # shape (m,n)

        cand_set = set(zip(D_x.ravel(), D_y.ravel()))

        best_cost = np.inf
        best_dx = best_dy = 0

        for dx, dy in cand_set:
            cost = np.abs(D_x - dx) + np.abs(D_y - dy)
            row_ind, col_ind = linear_sum_assignment(cost)
            total = cost[row_ind, col_ind].sum()
            if total < best_cost:
                best_cost = total
                best_dx, best_dy = dx, dy

        return int(best_cost)

    def reset(self, env):
        self.rewards = {agent: 0 for agent in env.agents.values()}
        wall_shape = np.full_like(env.grid, 'W', dtype=str)
        wall_shape[1:-1, 1:-1] = '.'
        wall_mesh = Mesh((0, 0), wall_shape, static=True, name='W')
        wall_mesh.place(env.grid, env.mesh_map)
        env.meshes.append(wall_mesh)
        num_agents = len(env.agents)
        self.target_shape = np.full((num_agents // 4 + 1, num_agents // 4 + 1), 'A', dtype=str)
        self.target_shape[1:-1, 1:-1] = '.'
        self.shape_desc = '\n'.join([' '.join([f'{self.target_shape[i, j]}'
                                     for j in range(self.target_shape.shape[1])])
                                     for i in range(self.target_shape.shape[0])])
        spread(env, 1, env.width - 2, 1, env.height - 2, self.rng)
        self.init_dis = self.emd(env.grid)
        self.prev_dis = self.init_dis
        self.cur_dis = self.init_dis
        self.score = 0

    def is_done(self, env):
        return self.cur_dis == 0

    def update(self, env, actions):
        self.prev_dis = self.cur_dis
        self.cur_dis = self.emd(env.grid)
        new_score = self.init_dis - self.cur_dis
        self.score = max(new_score, self.score)
        for name, mesh in env.agent_meshes.items():
            self.rewards[env.agents[name]] = (self.cur_dis - self.prev_dis) * 0.1

    def task_obs(self, agent):
        if agent is None:
            return {'score': self.score}
        return {}

    def desc(self):
        return (f'Your target is to properly align in the map and form'
                f'the following shape with other agents (A for agent):\n'
                f'{self.shape_desc}')


class Pursuit(Task):
    def __init__(self, seed=42):
        super().__init__(seed)
        self.prey = None
        self.score = 0
        self.rewards = {}
        self.prev_dis = {}

    def reset(self, env):
        self.rewards = {agent: 0 for agent in env.agents.values()}
        wall_shape = np.full_like(env.grid, 'W', dtype=str)
        wall_shape[1:-1, 1:-1] = '.'
        wall_mesh = Mesh((0, 0), wall_shape, static=True, name='W')
        wall_mesh.place(env.grid, env.mesh_map)
        prey_pos = (self.rng.randint(env.height // 2 + 1, env.height - 2),
                    self.rng.randint(env.width // 2 + 1, env.width - 2))
        self.prey = Mesh(prey_pos, np.full((1, 1), 'P', dtype=str),
                         static=False, name='P')
        self.prey.place(env.grid, env.mesh_map)
        spread(env, 1, max(env.height // 2, 5), 1, max(env.width // 2, 5), self.rng)
        self.score = 0
        self.prev_dis = {env.agents[name]: abs(mesh.pos[0] - self.prey.pos[0]) + abs(mesh.pos[1] - self.prey.pos[1])
                         for name, mesh in env.agent_meshes.items()}

    def subview(self, env, i, j):
        return env.grid[max(i - 4, 0):i + 4, max(j - 4, 0):j + 4]

    def danger(self, env, i, j):
        subview = self.subview(env, i, j)
        view_agents = (subview == 'A').sum()
        view_walls = (subview == 'W').sum()
        return view_agents + view_walls * 0.9

    def can_move_to(self, env, i, j):
        return 0 <= i < env.height and 0 <= j < env.width and env.grid[i, j] == '.'

    def update(self, env, actions):
        self.rewards = {agent: 0 for agent in env.agents.values()}
        for name, mesh in env.agent_meshes.items():
            dis = abs(mesh.pos[0] - self.prey.pos[0]) + abs(mesh.pos[1] - self.prey.pos[1])
            self.rewards[env.agents[name]] = self.prev_dis[env.agents[name]] - dis
        cnt = 0
        for di, dj in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            i, j = self.prey.pos
            if 0 <= i + di < env.height and 0 <= j + dj < env.width:
                cnt += env.grid[i + di, j + dj] != '.'
        if cnt == 4:
            self.score += 1
            danger = 1e6
            self.prey.remove(env.grid, env.mesh_map)
            self.prey = Mesh((0, 0), np.full((1, 1), 'P', dtype=str),
                             static=True, name='P')
            t = 0
            while t < env.height * env.width:
                i = self.rng.randint(1, env.height - 2)
                j = self.rng.randint(1, env.width - 2)
                if env.grid[i, j] != '.':
                    continue
                t += 1
                view_danger = self.danger(env, i, j)
                if view_danger < danger:
                    danger = view_danger
                    self.prey.pos = i, j
            self.prey.place(env.grid, env.mesh_map)
        else:
            i, j = self.prey.pos
            target = 0, 0, 0, 0
            danger = self.danger(env, i + di, j + dj)
            for di1, dj1 in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for di2, dj2 in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    di = di1 + di2
                    dj = dj1 + dj2
                    if (not self.can_move_to(env, i + di, j + dj)
                        or not self.can_move_to(env, i + di1, j + dj1)
                        or not self.can_move_to(env, i + di2, j + dj2)):
                        continue
                    view_danger = self.danger(env, i + di, j + dj)
                    if view_danger < danger:
                        danger = view_danger
                        target = di1, dj1, di2, dj2
            if target != (0, 0, 0, 0):
                self.prey.move(env.grid, env.mesh_map, target[0], target[1])
                self.prey.move(env.grid, env.mesh_map, target[2], target[3])
        self.prev_dis = {env.agents[name]: abs(mesh.pos[0] - self.prey.pos[0]) + abs(mesh.pos[1] - self.prey.pos[1])
                         for name, mesh in env.agent_meshes.items()}

    def task_obs(self, agent):
        return {'score': self.score}

    def desc(self):
        return (f'Target: There is a prey (denoted as P) somewhere on the map. '
                f'Your target is to cooperate with other agents to chase the prey down. '
                f'A prey is caught only when it is surrounded by 4 agents (A) or walls (W):\n'
                f'.,A/W,.\nA/W,P,A/W\n.,A/W,.\n'
                f'The prey moves faster than all of your kinds (2 steps each round). '
                f'Once it is caught, you will earn a point, and a new prey will spawn somewhere on the map.')


class Synchronization(Task):
    def __init__(self, seed=42):
        super().__init__(seed)
        self.agent_state = {}
        self.score = 0
        self.prev_state = -1
        self.rewards = {}

    def reset(self, env):
        self.rewards = {agent: 0 for agent in env.agents.values()}
        wall_shape = np.full_like(env.grid, 'W', dtype=str)
        wall_shape[1:-1, 1:-1] = '.'
        wall_mesh = Mesh((0, 0), wall_shape, static=True, name='W')
        wall_mesh.place(env.grid, env.mesh_map)
        self.score = 0
        self.agent_state = {name: bool(self.rng.randint(0, 1)) for name in env.agents}
        self.prev_state = -1
        spread(env, 1, env.width - 2, 1, env.height - 2, self.rng)
        for agent in env.agents.values():
            agent.valid_actions.append('SWITCH')
        for name in env.agents:
            i, j = env.agent_meshes[name].pos
            env.grid[i, j] = 'A' if self.agent_state[name] else 'a'
        self.score = 0

    def task_obs(self, agent):
        if agent is None:
            return {'score': self.score}
        return {'light_on': self.agent_state[agent.name]}

    def update(self, env, actions):
        for name, action in actions.items():
            if action.get('move', '') == 'SWITCH':
                self.agent_state[name] = not (self.agent_state[name])
            i, j = env.agent_meshes[name].pos
            env.grid[i, j] = 'A' if self.agent_state[name] else 'a'
        prev_score = self.score
        self.update_score()
        self.rewards = {agent: self.score - prev_score for agent in env.agents.values()}

    def update_score(self):
        state = sum(self.agent_state.values())
        if (state == len(self.agent_state) or state == 0) and state != self.prev_state:
            self.prev_state = state
            self.score += 1

    def desc(self):
        return ('Target: Each of you agents has a light that has two possible states: on/off. '
                'All of you need to synchronize your light states, i.e., all on or all off. '
                'You earn one point when all agents (including the ones out of your sight) have the same light states. '
                'And after this, all agents must synchronize their light states to the opposite in ordered to earn one another point. '
                'That means if you earned a point for synchronizing light states to all on, '
                'next time you earn a point is when light states are all off (the opposite), vice versa.\n'
                'There is one more action: SWITCH. '
                'When you choose SWITCH, light states will be changed to the opposite. '
                'In your view, agents with lights on are denoted in the regular way, '
                'while agents with lights off start with a dollar sign ($).')


class Foraging(Task):
    def __init__(self, seed=42):
        super().__init__(seed)
        self.food_mesh = None
        self.food_state = {}
        self.score = 0
        self.rewards = {}
        self.wall_mesh = None

    def reset(self, env):
        self.rewards = {agent: 0 for agent in env.agents.values()}
        wall_shape = np.full_like(env.grid, 'W', dtype=str)
        wall_shape[1:-1, 1:-1] = '.'

        food_i = self.rng.choice([1, env.height - 3])
        food_j = self.rng.choice([1, env.width - 3])
        nest_i = env.height - 3 if food_i == 1 else 1
        nest_j = env.width - 3 if food_j == 1 else 1

        if self.rng.randint(0, 1) == 0:
            walls = [n for n in range(4, env.height - 4, 4)]
            if len(walls) % 2 == 1:
                nest_j = 1
                food_j = 1
            for n, i in enumerate(walls):
                if n % 2 == 0:
                    wall_shape[i, :-env.width // 3 + 1] = 'W'
                else:
                    wall_shape[i, env.width // 3:] = 'W'
        else:
            walls = [n for n in range(4, env.width - 4, 4)]
            if len(walls) % 2 == 1:
                nest_i = 1
                food_i = 1
            for n, j in enumerate(walls):
                if n % 2 == 0:
                    wall_shape[:-env.height // 3 + 1, j] = 'W'
                else:
                    wall_shape[env.height // 3:, j] = 'W'

        wall_shape[nest_i:nest_i + 2, nest_j:nest_j + 2] = 'N'

        self.wall_mesh = Mesh((0, 0), wall_shape, static=True, name='W')
        self.wall_mesh.place(env.grid, env.mesh_map)

        self.food_mesh = Mesh((food_i, food_j), np.full((2, 2), 'F', dtype=str),
                              static=True, name='F')
        self.food_mesh.place(env.grid, env.mesh_map)
        self.food_state = {name: False for name in env.agents}
        spread(env, 1, env.width - 2, 1, env.height - 2, self.rng, 'a')
        self.score = 0

    def task_obs(self, agent):
        if agent is None:
            return {'score': self.score}
        return {'carrying_food': self.food_state[agent.name]}

    def near(self, env, pos, symbol):
        i, j = pos
        for di, dj in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            if not (0 <= i + di < env.width and 0 <= j + dj < env.height):
                continue
            if env.grid[i + di, j + dj] == symbol:
                return True

    def update(self, env, actions):
        for name, agent_mesh in env.agent_meshes.items():
            reward = 0
            i, j = agent_mesh.pos
            if self.food_state[name]:
                reward += max(0.05 - min([abs(i - self.wall_mesh.pos[0] - di) + abs(j - self.wall_mesh.pos[0] - dj)
                                          for di in range(self.wall_mesh.shape.shape[0]) for dj in
                                          range(self.wall_mesh.shape.shape[1])
                                          if self.wall_mesh.shape[di, dj] == 'N']) * 0.01, 0)
            else:
                reward += max(0.05 - min([abs(i - self.food_mesh.pos[0] - di) + abs(j - self.food_mesh.pos[0] - dj)
                                          for di in range(self.food_mesh.shape.shape[0]) for dj in
                                          range(self.food_mesh.shape.shape[1])]) * 0.01, 0)
            if self.near(env, agent_mesh.pos, 'F'):
                self.food_state[name] = True
                agent_mesh.shape[:, :] = 'A'
                agent_mesh.place(env.grid, env.mesh_map)
                reward = 0.5
            if self.near(env, agent_mesh.pos, 'N'):
                self.score += self.food_state[name]
                self.food_state[name] = False
                agent_mesh.shape[:, :] = 'a'
                agent_mesh.place(env.grid, env.mesh_map)
                reward = 0.5
            self.rewards[env.agents[name]] = reward

    def desc(self):
        return ('Target: You are in a maze where walls (W) blocks your way. '
                'Your task is to find a path and carry food (F) to your nest (N). '
                'To carry one piece of food to your nest, you must follow these steps:\n'
                '1. If you are not carrying food, find the food source (F), pick up a piece of it and leave'
                '(food is infinite, you can only carry one piece at a time).\n'
                '2. If you are carrying food, find a path to the nest (N), drop the food and leave, then you earn a point.\n'
                'Move as many pieces of food to the nest as possible.\n'
                'Note that only agents that are directly adjacent to F/N can pick up/drop the food. '
                'Agents carrying food are denoted in the regular way, while others start with a dollar sign ($).')
