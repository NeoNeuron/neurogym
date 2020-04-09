"""Plotting functions."""

import glob
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

import gym


mpl.rcParams['font.size'] = 7
mpl.rcParams['pdf.fonttype'] = 42
mpl.rcParams['ps.fonttype'] = 42
mpl.rcParams['font.family'] = 'arial'


def plot_env(env, num_steps=200, num_trials=None, def_act=None, model=None,
             name=None, legend=True, obs_traces=[], fig_kwargs={}, folder=''):
    """Plot environment with agent.

    Args:
        env: already built neurogym task or name of it
        num_steps: number of steps to run the task
        num_trials: if not None, the number of trials to run
        def_act: if not None (and model=None), the task will be run with the
                 specified action
        model: if not None, the task will be run with the actions predicted by
               model, which so far is assumed to be created and trained with the
               stable-baselines toolbox:
                   (https://github.com/hill-a/stable-baselines)
        name: title to show on the rewards panel
        legend: whether to show the legend for actions panel or not.
        obs_traces: if != [] observations will be plot as traces, with the labels
                    specified by obs_traces
        fig_kwargs: figure properties admited by matplotlib.pyplot.subplots() fun.
    """
    # We don't use monitor here because:
    # 1) env could be already prewrapped with monitor
    # 2) monitor will save data and so the function will need a folder

    if isinstance(env, str):
        env = gym.make(env)
    if name is None:
        name = type(env).__name__
    data = run_env(env=env, num_steps=num_steps, num_trials=num_trials,
                   def_act=def_act, model=model)

    fig = fig_(
        data['obs'], data['actions'],
        gt=data['gt'], rewards=data['rewards'],
        legend=legend, performance=data['perf'],
        states=data['states'], name=name, obs_traces=obs_traces,
        fig_kwargs=fig_kwargs, env=env, folder=folder
    )

    return fig


def run_env(env, num_steps=200, num_trials=None, def_act=None, model=None):
    observations = []
    obs_cum = []
    state_mat = []
    rewards = []
    actions = []
    actions_end_of_trial = []
    gt = []
    perf = []
    obs = env.reset()  # TODO: not saving this first observation
    obs_cum_temp = obs

    if num_trials is not None:
        num_steps = 1e5  # Overwrite num_steps value

    trial_count = 0
    for stp in range(int(num_steps)):
        if model is not None:
            action, _states = model.predict(obs)
            if isinstance(action, float) or isinstance(action, int):
                action = [action]
            if len(_states) > 0:
                state_mat.append(_states)
        elif def_act is not None:
            action = def_act
        else:
            action = env.action_space.sample()
        obs, rew, done, info = env.step(action)
        obs_cum_temp += obs
        obs_cum.append(obs_cum_temp.copy())
        if isinstance(info, list):
            info = info[0]
            obs_aux = obs[0]
            rew = rew[0]
            done = done[0]
            action = action[0]
        else:
            obs_aux = obs

        if done:
            env.reset()
        observations.append(obs_aux)
        rewards.append(rew)
        actions.append(action)
        if 'gt' in info.keys():
            gt.append(info['gt'])
        else:
            gt.append(0)

        if info['new_trial']:
            actions_end_of_trial.append(action)
            perf.append(info['performance'])
            obs_cum_temp = np.zeros_like(obs_cum_temp)
            trial_count += 1
            if num_trials is not None and trial_count >= num_trials:
                break
        else:
            actions_end_of_trial.append(-1)
            perf.append(-1)

    if model is not None and len(state_mat) > 0:
        states = np.array(state_mat)
        states = states[:, 0, :]
    else:
        states = None

    data = {
        'obs': np.array(observations),
        'obs_cum': np.array(obs_cum),
        'rewards': rewards,
        'actions': actions,
        'perf': perf,
        'actions_end_of_trial': actions_end_of_trial,
        'gt': gt,
        'states': states
    }
    return data


def fig_(obs, actions, gt=None, rewards=None, performance=None, states=None,
         legend=True, obs_traces=None, name='', folder='', fig_kwargs={},
         env=None):
    """Visualize a run in a simple environment.

    Args:
        obs: np array of observation (n_step, n_unit)
        actions: np array of action (n_step, n_unit)
        gt: np array of groud truth
        rewards: np array of rewards
        performance: np array of performance
        states: np array of network states
        name: title to show on the rewards panel and name to save figure
        folder: if != '', where to save the figure
        legend: whether to show the legend for actions panel or not.
        obs_traces: None or list.
            If list, observations will be plot as traces, with the labels
            specified by obs_traces
        fig_kwargs: figure properties admited by matplotlib.pyplot.subplots() fun.
        env: environment class for extra information
    """
    obs = np.array(obs)
    actions = np.array(actions)

    return _plot_env_1dbox(
        obs, actions, gt=gt, rewards=rewards,
        performance=performance, states=states, legend=legend,
        obs_traces=obs_traces, name=name, folder=folder,
        fig_kwargs=fig_kwargs, env=env
    )


def _plot_env_1dbox(
        obs, actions, gt=None, rewards=None, performance=None, states=None,
        legend=True, obs_traces=None, name='', folder='', fig_kwargs={},
        env=None):
    """Plot environment with 1-D Box observation space."""
    if len(obs.shape) != 2:
        raise ValueError('obs has to be 2-dimensional.')
    steps = np.arange(obs.shape[0])  # XXX: +1? 1st obs doesn't have action/gt

    n_row = 2  # observation and action
    n_row += rewards is not None
    n_row += performance is not None
    n_row += states is not None

    gt_colors = 'gkmcry'
    if not fig_kwargs:
        fig_kwargs = dict(sharex=True, figsize=(5, n_row*1.2))

    f, axes = plt.subplots(n_row, 1, **fig_kwargs)
    i_ax = 0
    # obs
    ax = axes[i_ax]
    i_ax += 1
    if obs_traces:
        assert len(obs_traces) == obs.shape[1],\
            'Please provide label for each trace in the observations'
        for ind_tr, tr in enumerate(obs_traces):
            ax.plot(obs[:, ind_tr], label=obs_traces[ind_tr])
        ax.legend()
        ax.set_xlim([-0.5, len(steps)-0.5])
    else:
        ax.imshow(obs.T, aspect='auto', origin='lower')
        if env and env.ob_dict:
            # Plot environment annotation
            yticks = []
            yticklabels = []
            for key, val in env.ob_dict.items():
                yticks.append((np.min(val)+np.max(val))/2)
                yticklabels.append(key)
            ax.set_yticks(yticks)
            ax.set_yticklabels(yticklabels)
        else:
            ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['right'].set_visible(False)

    if name:
        ax.set_title(name + ' env')
    ax.set_ylabel('Observations')

    # actions
    ax = axes[i_ax]
    i_ax += 1
    if len(actions.shape) > 1:
        # Changes not implemented yet
        ax.plot(steps, actions, marker='+', label='Actions')
    else:
        ax.plot(steps, actions, marker='+', label='Actions')
    if gt is not None:
        gt = np.array(gt)
        if len(gt.shape) > 1:
            for ind_gt in range(gt.shape[1]):
                ax.plot(steps, gt[:, ind_gt], '--'+gt_colors[ind_gt],
                        label='Ground truth '+str(ind_gt))
        else:
            ax.plot(steps, gt, '--'+gt_colors[0], label='Ground truth')
    ax.set_xlim([-0.5, len(steps)-0.5])
    ax.set_ylabel('Actions')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if legend:
        ax.legend()
    if env and env.act_dict:
        # Plot environment annotation
        yticks = []
        yticklabels = []
        for key, val in env.act_dict.items():
            yticks.append((np.min(val) + np.max(val)) / 2)
            yticklabels.append(key)
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)

    # rewards
    if rewards is not None:
        ax = axes[i_ax]
        i_ax += 1
        ax.plot(steps, rewards, 'r', label='Rewards')
        ax.set_ylabel('Reward')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if legend:
            ax.legend()
        ax.set_xlim([-0.5, len(steps)-0.5])

        if env and env.rewards:
            # Plot environment annotation
            yticks = []
            yticklabels = []
            for key, val in env.rewards.items():
                yticks.append(val)
                yticklabels.append('{:s} {:0.2f}'.format(key, val))
            ax.set_yticks(yticks)
            ax.set_yticklabels(yticklabels)

    if performance is not None:
        ax = axes[i_ax]
        i_ax += 1
        ax.plot(steps, performance, 'k', label='Performance')
        ax.set_ylabel('Performance')
        performance = np.array(performance)
        mean_perf = np.mean(performance[performance != -1])
        ax.set_title('Mean performance: ' + str(np.round(mean_perf, 2)))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if legend:
            ax.legend()
        ax.set_xlim([-0.5, len(steps)-0.5])

    # states
    if states is not None:
        ax.set_xticks([])
        ax = axes[i_ax]
        i_ax += 1
        plt.imshow(states[:, int(states.shape[1]/2):].T,
                   aspect='auto')
        ax.set_title('Activity')
        ax.set_ylabel('Neurons')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    ax.set_xlabel('Steps')
    plt.tight_layout()
    if folder is not None and folder != '':
        if folder.endswith('.png') or folder.endswith('.svg'):
            f.savefig(folder)
        else:
            f.savefig(folder + name + 'env_struct.png')
        plt.close(f)
    return f


def plot_rew_across_training(folder, window=500, ax=None,
                             fkwargs={'c': 'tab:blue'}, ytitle='',
                             legend=False, zline=False, metric_name='reward'):
    data = put_together_files(folder)
    if data:
        sv_fig = False
        if ax is None:
            sv_fig = True
            f, ax = plt.subplots(figsize=(8, 8))
        metric = data[metric_name]
        if isinstance(window, float):
            if window < 1.0:
                window = int(metric.size * window)
        mean_metric = np.convolve(metric, np.ones((window,))/window,
                                  mode='valid')
        ax.plot(mean_metric, **fkwargs)  # add color, label etc.
        ax.set_xlabel('trials')
        if not ytitle:
            ax.set_ylabel('mean ' + metric_name + ' (running window' +
                          ' of {:d} trials)'.format(window))
        else:
            ax.set_ylabel(ytitle)
        if legend:
            ax.legend()
        if zline:
            ax.axhline(0, c='k', ls=':')
        if sv_fig:
            f.savefig(folder + '/mean_' + metric_name + '_across_training.png')
    else:
        print('No data in: ', folder)


def put_together_files(folder):
    files = glob.glob(folder + '/*_bhvr_data*npz')
    data = {}
    if len(files) > 0:
        files = order_by_sufix(files)
        file_data = np.load(files[0], allow_pickle=True)
        for key in file_data.keys():
            data[key] = file_data[key]

        for ind_f in range(1, len(files)):
            file_data = np.load(files[ind_f], allow_pickle=True)
            for key in file_data.keys():
                data[key] = np.concatenate((data[key], file_data[key]))
        np.savez(folder + '/bhvr_data_all.npz', **data)
    return data


def order_by_sufix(file_list):
    sfx = [int(x[x.rfind('_')+1:x.rfind('.')]) for x in file_list]
    sorted_list = [x for _, x in sorted(zip(sfx, file_list))]
    return sorted_list


if __name__ == '__main__':
    f = '/home/molano/res080220/SL_PerceptualDecisionMaking-v0_0/'
    plot_rew_across_training(folder=f)
