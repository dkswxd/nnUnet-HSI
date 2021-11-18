_base_ = [
    '../_base_/models/upernet_swing1.py', '../_base_/datasets/hsic6.py',
    '../_base_/default_runtime.py', '../_base_/schedules/schedule_4k.py'
]

norm_cfg = dict(type='BN', requires_grad=True) # for single GPU training

model = dict(
    pretrained='pretrain/swin_small_patch4_window7_224.pth',
    backbone=dict(
        embed_dims=96,
        depths=[2, 2, 18, 2],
        num_heads=[3, 6, 12, 24],
        window_size=7,
        use_abs_pos_embed=False,
        drop_path_rate=0.3,
        patch_norm=True,
        in_channels=3),
    decode_head=dict(
        in_channels=[96 * 6, 192 * 6, 384 * 6, 768 * 6],
        num_classes=2,
        norm_cfg=norm_cfg),
    auxiliary_head=dict(
        in_channels=384 * 6,
        num_classes=2,
        norm_cfg=norm_cfg))

# AdamW optimizer, no weight decay for position embedding & layer norm
# in backbone
optimizer = dict(
    _delete_=True,
    type='AdamW',
    lr=0.00006,
    betas=(0.9, 0.999),
    weight_decay=0.01,
    paramwise_cfg=dict(
        custom_keys={
            'absolute_pos_embed': dict(decay_mult=0.),
            'relative_position_bias_table': dict(decay_mult=0.),
            'norm': dict(decay_mult=0.)
        }))

lr_config = dict(
    _delete_=True,
    policy='poly',
    warmup='linear',
    warmup_iters=1500,
    warmup_ratio=1e-6,
    power=1.0,
    min_lr=0.0,
    by_epoch=False)

# By default, models are trained on 8 GPUs with 2 images per GPU
data = dict(samples_per_gpu=2)